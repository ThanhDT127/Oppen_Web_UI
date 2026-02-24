"""
Chat completions endpoint with streaming support.
"""

import uuid
import json
import asyncio
from datetime import datetime, timezone
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

from config import LITELLM_BASE, LITELLM_KEY, logger
from core.auth import require_user, assert_model_allowed, load_users, save_users, get_lock
from core.quota import maybe_reset_quota, enforce_and_bump_quota
from core.cost import calc_cost_usd, append_pending, remove_pending, load_prices, calc_image_cost_from_body
from core.audit_state import init_audit_state, set_usage_state, set_error_state, set_counters
from services.litellm import get_cost_from_headers, find_usage_in_log
from utils.helpers import truncate_text, extract_text_from_messages, safe_headers
from utils.logging import detail_log, write_audit_line


def _is_image_generation_model(model: str) -> bool:
    """Check if model is an image generation model."""
    if not isinstance(model, str):
        return False
    model_lower = model.lower()
    # Check for renamed models that bypass OpenWebUI filter
    return any(pattern in model_lower for pattern in [
        "image", "dall-e", "dalle", "stable-diffusion", "midjourney", "imagen",
        "-draw", "draw-",  # detect renamed models like gpt-draw-1
        "img-"  # detect models like img-gemini-flash, img-gpt-dalle-3
    ])


# --- Task prompt detection (Fix #3) ---
_TASK_PATTERNS = [
    "### Task:\nGenerate a concise",       # title generation
    "### Task:\nGenerate 1-3 broad tags",  # tag generation
    "### Task:\nGenerate follow-up",       # follow-up suggestions
    "### Task:\nGenerate a query",         # search query generation
]


def _is_system_task_prompt(messages: list) -> str | None:
    """
    Detect Open WebUI internal task prompts (title/tags/follow-up generation).
    These should NOT be sent to image models.
    
    Returns:
        Task type string ('title', 'tags', 'follow_up', 'query') if detected, else None.
    """
    prompt = _extract_prompt_from_messages(messages)
    if not prompt:
        return None
    for pattern in _TASK_PATTERNS:
        if pattern in prompt:
            if "title" in pattern.lower():
                return "title"
            elif "tags" in pattern.lower():
                return "tags"
            elif "follow-up" in pattern.lower():
                return "follow_up"
            else:
                return "query"
    return None


def _extract_prompt_from_messages(messages: list) -> str:
    """Extract text prompt from last user message (for logging/display)."""
    if not isinstance(messages, list):
        return ""
    
    # Get last user message
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content")
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                # Extract text from content array
                texts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(item.get("text", ""))
                return " ".join(texts)
    return ""


def _prepare_image_messages(messages: list) -> list:
    """
    Prepare full conversation messages for Gemini image generation.
    Keeps conversation context so Gemini can understand references
    like "ảnh đấy" or "vẽ lại ảnh này" in follow-up messages.
    
    Cleans up messages by:
    - Keeping all user and assistant messages
    - Stripping assistant markdown image references (Gemini doesn't need them)
    - Preserving image_url content parts (for image editing)
    """
    if not isinstance(messages, list):
        return []
    
    cleaned = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "system":
            # Keep system messages as-is
            cleaned.append({"role": role, "content": content})
        elif role == "user":
            # Keep user messages fully (text + images)
            cleaned.append({"role": role, "content": content})
        elif role == "assistant":
            # For assistant messages, extract meaningful text
            # Remove markdown image links that Gemini can't use
            if isinstance(content, str):
                import re
                # Remove ![...](...) markdown images
                text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', content)
                text = text.replace("Here is the image you requested.", "").strip()
                if text:
                    cleaned.append({"role": role, "content": text})
                else:
                    # If only had image, add a short note
                    cleaned.append({"role": role, "content": "[I generated an image based on your request]"})
            else:
                cleaned.append({"role": role, "content": content})
    
    return cleaned if cleaned else []


def _build_contextual_prompt(messages: list, last_prompt: str) -> str:
    """
    Build a rich text prompt for GPT Image models from conversation history.
    
    GPT Image models only accept text prompts via /images/generations,
    so we combine conversation context into a single descriptive prompt.
    This helps the model understand references like "that image" or "modify it".
    
    Args:
        messages: Full conversation messages from Open WebUI
        last_prompt: The extracted last user message text
    
    Returns:
        A contextual prompt string with conversation summary
    """
    if not isinstance(messages, list) or len(messages) <= 1:
        return last_prompt
    
    context_parts = []
    has_image = False
    
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "user":
            # Check for image content
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "image_url":
                            has_image = True
                            context_parts.append("[User uploaded an image]")
                        elif item.get("type") == "text":
                            text = item.get("text", "").strip()
                            if text:
                                context_parts.append(f"User: {text}")
            elif isinstance(content, str) and content.strip():
                context_parts.append(f"User: {content.strip()}")
        
        elif role == "assistant":
            if isinstance(content, str):
                # Summarize assistant responses briefly
                import re
                text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '[generated image]', content)
                text = text.strip()
                if text and len(text) < 200:
                    context_parts.append(f"Assistant: {text}")
                elif text:
                    context_parts.append(f"Assistant: {text[:150]}...")
    
    # If only one message or no useful context, return original prompt
    if len(context_parts) <= 1:
        return last_prompt
    
    # Build contextual prompt
    context_summary = "\n".join(context_parts)
    
    if has_image:
        contextual = (
            f"Context of our conversation:\n{context_summary}\n\n"
            f"The user has uploaded an image in this conversation. "
            f"Based on the conversation context above, fulfill this request:\n{last_prompt}"
        )
    else:
        contextual = (
            f"Context of our conversation:\n{context_summary}\n\n"
            f"Based on the conversation context above, generate an image for:\n{last_prompt}"
        )
    
    return contextual


def _extract_images_from_messages(messages: list) -> list[str]:
    """
    Extract image URLs/base64 uploaded by the USER from conversation messages.
    
    Only scans USER messages (not assistant) to avoid including AI-generated images.
    Returns a list of image URLs (data:image/...;base64,... or http URLs).
    """
    image_urls = []
    if not isinstance(messages, list):
        return image_urls
    
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        # Only extract from user messages — skip assistant-generated images
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "")
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "image_url":
                    img_url_obj = item.get("image_url", {})
                    if isinstance(img_url_obj, dict):
                        url = img_url_obj.get("url", "")
                        if url and (url.startswith("data:image") or url.startswith("http")):
                            image_urls.append(url)
                    elif isinstance(img_url_obj, str):
                        if img_url_obj.startswith("data:image") or img_url_obj.startswith("http"):
                            image_urls.append(img_url_obj)
    
    return image_urls


async def _handle_image_as_chat(request: Request, user: dict, model: str, body: dict):
    """
    Handle image generation models in chat format.
    Converts chat request to image generation, then formats response as chat.
    """
    rid = init_audit_state(request, user["user_id"], "/v1/chat/completions", model)
    
    # Extract messages and prompt
    messages = body.get("messages", [])
    prompt = _extract_prompt_from_messages(messages)
    
    if not prompt:
        raise HTTPException(400, "No prompt found in messages for image generation")
    
    # Fix #3: Detect and skip Open WebUI task prompts (title/tags generation)
    task_type = _is_system_task_prompt(messages)
    if task_type:
        detail_log(
            "chat.task_skipped",
            request=request,
            user_id=user.get("user_id"),
            model=model,
            task_type=task_type,
            reason="Task prompt sent to image model, returning dummy response",
        )
        # Return appropriate dummy response based on task type
        if task_type == "title":
            dummy_content = '{"title": "🎨 Image Generation"}'
        elif task_type == "tags":
            dummy_content = '{"tags": ["Art", "Image Generation"]}'
        elif task_type == "follow_up":
            dummy_content = '{"follow_ups": ["Generate another image", "Modify the image"]}'
        else:
            dummy_content = '{"query": "image generation"}'
        
        chat_response = {
            "id": f"chatcmpl-{rid}",
            "object": "chat.completion",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": dummy_content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
        # Handle streaming for task prompts too
        if body.get("stream", False):
            async def _stream_task():
                chunk = {"id": f"chatcmpl-{rid}", "object": "chat.completion.chunk", "created": int(datetime.now(timezone.utc).timestamp()), "model": model, "choices": [{"index": 0, "delta": {"role": "assistant", "content": dummy_content}, "finish_reason": None}]}
                yield f"data: {json.dumps(chunk)}\n\n"
                finish = {"id": f"chatcmpl-{rid}", "object": "chat.completion.chunk", "created": int(datetime.now(timezone.utc).timestamp()), "model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
                yield f"data: {json.dumps(finish)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(_stream_task(), media_type="text/event-stream")
        return JSONResponse(status_code=200, content=chat_response)
    
    detail_log(
        "chat.image_model",
        request=request,
        user_id=user.get("user_id"),
        model=model,
        prompt=truncate_text(prompt, limit=2000),
    )
    
    assert_model_allowed(user, model)
    maybe_reset_quota(user)
    
    # Fix #1: Prepare full conversation messages for context
    image_messages = _prepare_image_messages(messages)
    
    # Prepare image generation request (for non-Gemini fallback)
    image_body = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": body.get("size", "1024x1024"),
    }
    
    # Call image generation API
    client: httpx.AsyncClient = request.app.state.http_client
    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "Content-Type": "application/json",
        "X-Request-ID": rid,
    }
    
    try:
        # Gemini models use chat/completions with full conversation context
        if "gemini" in model.lower():
            from api.images import _generate_image_via_chat
            image_data = await _generate_image_via_chat(client, headers, image_messages, model)
        else:
            # GPT Image / DALL-E models
            # Check if user uploaded images → use /images/edits for editing
            uploaded_images = _extract_images_from_messages(messages)
            contextual_prompt = _build_contextual_prompt(messages, prompt)
            
            from api.images import _IMAGE_MODEL_MAP
            litellm_model = _IMAGE_MODEL_MAP.get(model, model)
            


            
            if uploaded_images and "dalle" not in model.lower():
                # User uploaded image(s) → use /images/edits endpoint
                detail_log(
                    "chat.image_edit",
                    request=request,
                    user_id=user.get("user_id"),
                    model=model,
                    num_images=len(uploaded_images),
                    prompt=truncate_text(prompt, limit=200),
                )
                from api.images import _generate_via_gpt_image_edit
                image_data = await _generate_via_gpt_image_edit(
                    client, headers, uploaded_images, contextual_prompt,
                    model, size=body.get("size", "1024x1024"),
                )
                # If edit failed to extract images, fall back to generations
                if image_data is None:
                    detail_log("chat.image_edit_fallback", request=request,
                               reason="No valid images extracted, falling back to generations")
                    image_body["prompt"] = contextual_prompt
                    image_body["model"] = litellm_model
                    resp = await client.post(
                        f"{LITELLM_BASE}/images/generations",
                        headers=headers, json=image_body, timeout=120
                    )
                    if resp.status_code >= 400:
                        set_error_state(request, "provider", f"Image generation returned {resp.status_code}")
                        try: raise HTTPException(resp.status_code, resp.json())
                        except: raise HTTPException(resp.status_code, resp.text)
                    image_data = resp.json()
            else:
                # No uploaded images → use /images/generations with contextual prompt
                image_body["prompt"] = contextual_prompt
                image_body["model"] = litellm_model
                
                resp = await client.post(
                    f"{LITELLM_BASE}/images/generations",
                    headers=headers,
                    json=image_body,
                    timeout=120
                )
                if resp.status_code >= 400:
                    set_error_state(request, "provider", f"Image generation returned {resp.status_code}")
                    try:
                        error_data = resp.json()
                        raise HTTPException(resp.status_code, error_data)
                    except Exception:
                        raise HTTPException(resp.status_code, resp.text)
                image_data = resp.json()
    
    except httpx.RequestError as e:
        set_error_state(request, "provider", f"Image generation failed: {e.__class__.__name__}")
        raise HTTPException(503, f"Image generation unavailable: {e.__class__.__name__}")
    
    # Parse image response and materialize base64 to HTTP URL
    # CRITICAL: data:image/png;base64,... URLs are hundreds of KB and cause
    # "Chunk too big" errors in Open WebUI streaming. Must convert to HTTP URLs.
    image_url = None
    if isinstance(image_data.get("data"), list) and len(image_data["data"]) > 0:
        from utils.media import maybe_materialize_image_items
        maybe_materialize_image_items(request, image_data["data"], fallback_mime="image/png")
        image_url = image_data["data"][0].get("url")
    
    # Calculate cost and bump quota
    prices = load_prices()
    cost_usd = calc_image_cost_from_body(model, image_body, prices)
    if cost_usd > 0:
        enforce_and_bump_quota(user["user_id"], add_cost_usd=cost_usd, add_image_requests=1)
    
    set_usage_state(request, 0, 0, 0, cost_usd)
    set_counters(request, image_count=1)
    
    # Format as chat completion response
    content_text = f"![Generated Image]({image_url})\n\nHere is the image you requested." if image_url else "Sorry, I could not generate the image. Please try again."
    chat_response = {
        "id": f"chatcmpl-{rid}",
        "object": "chat.completion",
        "created": int(datetime.now(timezone.utc).timestamp()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content_text
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        },
        "_mw_user": user["user_id"],
        "_mw_request_id": rid,
        "_mw_added_cost_usd": round(cost_usd, 6) if cost_usd > 0 else None
    }
    
    # Handle streaming vs non-streaming
    stream = body.get("stream", False)
    if stream:
        # Convert to SSE stream format
        async def _stream_image_response():
            # Send data chunk
            chunk = {
                "id": f"chatcmpl-{rid}",
                "object": "chat.completion.chunk",
                "created": int(datetime.now(timezone.utc).timestamp()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        "content": content_text
                    },
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            
            # Send finish chunk
            finish_chunk = {
                "id": f"chatcmpl-{rid}",
                "object": "chat.completion.chunk",
                "created": int(datetime.now(timezone.utc).timestamp()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(finish_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(_stream_image_response(), media_type="text/event-stream")
    else:
        return JSONResponse(status_code=200, content=chat_response)


async def _finalize_streaming(request: Request, user: dict, model: str, request_id: str, usage_data: dict):
    """
    Finalize streaming request: Calculate cost, bump quota, write reconciled audit.
    
    Args:
        request: FastAPI Request
        user: User dict
        model: Model name
        request_id: Request ID
        usage_data: Usage dict from stream (if stream_options.include_usage), or None
    """
    try:
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        cost_usd = 0.0
        usage_missing = False
        
        # Method 1: Extract from stream (if stream_options.include_usage was set)
        if usage_data:
            prompt_tokens = int(usage_data.get("prompt_tokens", 0))
            completion_tokens = int(usage_data.get("completion_tokens", 0))
            total_tokens = int(usage_data.get("total_tokens", prompt_tokens + completion_tokens))
            logger.info("stream_finalize rid=%s tokens=%d (from stream)", request_id, total_tokens)
        
        # Method 2: Fallback to LiteLLM log parsing
        else:
            await asyncio.sleep(1)  # Wait for LiteLLM to write log
            usage = find_usage_in_log(request_id)
            if usage:
                prompt_tokens = int(usage.get("prompt_tokens", 0))
                completion_tokens = int(usage.get("completion_tokens", 0))
                total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
                logged_cost = usage.get("response_cost")
                if logged_cost:
                    try:
                        cost_usd = float(logged_cost)
                    except Exception:
                        pass
                logger.info("stream_finalize rid=%s tokens=%d (from litellm log)", request_id, total_tokens)
        
        # CRITICAL: If no usage found, mark as missing and don't write reconciled audit
        if total_tokens == 0 and cost_usd == 0.0:
            usage_missing = True
            logger.warning("stream_finalize rid=%s: USAGE MISSING - no tokens or cost from stream or log", request_id)
            # Don't write reconciled audit with zeros - this would pollute billable metrics
            # The pending audit remains, showing the request was made but usage wasn't captured
            return
        
        # Calculate cost if not from LiteLLM
        if cost_usd == 0.0 and total_tokens > 0:
            prices = load_prices()
            cost_usd = calc_cost_usd(model, prompt_tokens, completion_tokens, prices)
        
        # Bump quota (CRITICAL for billing)
        if total_tokens > 0 or cost_usd > 0:
            lock = get_lock()
            with lock:
                users = load_users()
                for u in users:
                    if u.get("user_id") == user["user_id"]:
                        maybe_reset_quota(u)
                        u["used_tokens"] = u.get("used_tokens", 0) + total_tokens
                        u["used_cost_usd"] = u.get("used_cost_usd", 0.0) + cost_usd
                        quota = u.setdefault("quota", {})
                        quota["used_tokens"] = quota.get("used_tokens", 0) + total_tokens
                        quota["used_cost_usd"] = quota.get("used_cost_usd", 0.0) + cost_usd
                        break
                save_users(users)
        
        # Write reconciled audit line (only if we have actual usage)
        write_audit_line({
            "ts": datetime.now(timezone.utc).isoformat(),
            "rid": request_id,
            "user_id": user["user_id"],
            "endpoint": "/v1/chat/completions",
            "model": model,
            "status": "reconciled",
            "status_code": 200,
            "latency_ms": None,
            "tokens_in": prompt_tokens,
            "tokens_out": completion_tokens,
            "tokens_total": total_tokens,
            "cost_usd": cost_usd,
            "image_count": None,
            "tts_chars": None,
            "stt_seconds": None,
            "video_count": None,
            "error_type": None,
            "error_message": None
        })
        
        logger.info("stream_finalize_complete rid=%s tokens=%d cost=$%.6f", request_id, total_tokens, cost_usd)
    
    except Exception as e:
        logger.error("stream_finalize_error rid=%s: %s", request_id, str(e))


async def chat_completions(request: Request):
    """
    Proxy chat completions to LiteLLM with quota enforcement.
    Supports both streaming and non-streaming modes.
    Also handles image generation models by converting to chat format.
    """
    user = require_user(request)

    # Parse body once and reuse
    try:
        body = await request.json()
    except UnicodeDecodeError as e:
        raise HTTPException(400, f"Invalid UTF-8 encoding in request body: {str(e)}")
    
    model = body.get("model")
    if not model:
        raise HTTPException(400, "Missing model")
    
    # Detect image generation models and route to image generation
    is_image_model = _is_image_generation_model(model)
    if is_image_model:
        return await _handle_image_as_chat(request, user, model, body)
    
    # Initialize audit state early
    rid = init_audit_state(request, user["user_id"], "/v1/chat/completions", model)

    # Process multimodal content (images, documents, and other file attachments in messages)
    messages = body.get("messages")
    if isinstance(messages, list):
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            if isinstance(content, list):
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    
                    # Handle image_url content type
                    if item.get("type") == "image_url":
                        image_url_obj = item.get("image_url")
                        if isinstance(image_url_obj, dict):
                            url = image_url_obj.get("url")
                            if isinstance(url, str) and url.startswith("data:"):
                                # Keep data URLs inline - don't materialize 
                                # LiteLLM has issues downloading from localhost
                                pass
                    
                    # Handle file attachments (documents, PDFs, etc.)
                    # Some models accept file content in various formats
                    elif item.get("type") in ("file", "document", "attachment"):
                        # Check for data URL in various fields
                        for url_field in ["url", "file_url", "data"]:
                            url = item.get(url_field)
                            if isinstance(url, str) and url.startswith("data:"):
                                # Keep data URLs inline
                                pass
                                break
                    
                    # Handle generic data URLs in any content item
                    elif "url" in item:
                        url = item.get("url")
                        if isinstance(url, str) and url.startswith("data:"):
                            # Keep data URLs inline
                            pass

    prompt_preview = extract_text_from_messages(body.get("messages"))
    detail_log(
        "chat.request",
        request=request,
        user_id=user.get("user_id"),
        model=model,
        stream=bool(body.get("stream")),
        prompt=truncate_text(prompt_preview, limit=2000),
        body=body,
    )

    assert_model_allowed(user, model)

    maybe_reset_quota(user)
    quota = user.get("quota", {})
    limit_tokens = int(quota.get("limit_tokens", 0))
    used_tokens = int(quota.get("used_tokens", 0))
    limit_cost = float(quota.get("limit_cost_usd", 0.0))
    used_cost = float(quota.get("used_cost_usd", 0.0))

    # OpenAI's newest reasoning-first models may treat `max_tokens` differently.
    # When users chat via OpenWebUI, it often sends `max_tokens`.
    # For gpt-5*, translate to `max_completion_tokens` to avoid responses that spend all tokens
    # on reasoning and return empty visible content.
    if isinstance(model, str) and model.startswith("gpt-5"):
        if "max_tokens" in body and "max_completion_tokens" not in body:
            body["max_completion_tokens"] = body.get("max_tokens")
            body.pop("max_tokens", None)

    # Use rid from audit_state (already generated)
    request_id = rid
    body["user"] = user["user_id"]
    metadata = body.get("metadata") or {}
    metadata["mw_request_id"] = request_id
    body["metadata"] = metadata

    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    is_stream = bool(body.get("stream"))

    if is_stream:
        return await _handle_streaming(request, user, model, body, headers, request_id)
    else:
        return await _handle_non_streaming(request, user, model, body, headers, request_id, limit_tokens, used_tokens, limit_cost, used_cost)


async def _handle_streaming(request: Request, user: dict, model: str, body: dict, headers: dict, request_id: str):
    """Handle streaming chat completions"""
    from utils.logging import write_audit_line
    from core.audit_state import mark_audit_logged
    from datetime import datetime, timezone
    
    # Write pending audit line immediately before streaming
    write_audit_line({
        "ts": datetime.now(timezone.utc).isoformat(),
        "rid": request_id,
        "user_id": user["user_id"],
        "endpoint": "/v1/chat/completions",
        "model": model,
        "status": "pending",
        "status_code": None,
        "latency_ms": None,
        "tokens_in": 0,
        "tokens_out": 0,
        "tokens_total": 0,
        "cost_usd": 0.0,
        "image_count": None,
        "tts_chars": None,
        "stt_seconds": None,
        "video_count": None,
        "error_type": None,
        "error_message": None
    })
    
    # Mark as logged to prevent middleware from logging again
    mark_audit_logged(request)
    
    append_pending(request_id, user["user_id"])

    # Important: like TTS, don't create the upstream stream inside an `async with` that
    # exits before StreamingResponse iterates. We open the stream first, validate status,
    # then stream bytes and always clean up.
    logger.info("stream_start rid=%s model=%s", request_id, model)

    client = httpx.AsyncClient(timeout=600)
    detail_log(
        "upstream.request",
        request=request,
        rid=request_id,
        user_id=user.get("user_id"),
        upstream=f"{LITELLM_BASE}/chat/completions",
        method="POST",
        headers=safe_headers(headers),
        body=body,
    )
    req = client.build_request("POST", f"{LITELLM_BASE}/chat/completions", headers=headers, json=body)
    resp = await client.send(req, stream=True)

    if resp.status_code >= 400:
        try:
            error_bytes = await resp.aread()
        finally:
            error_text = error_bytes.decode("utf-8", errors="ignore")
            
            # Write error audit to close the pending request
            write_audit_line({
                "ts": datetime.now(timezone.utc).isoformat(),
                "rid": request_id,
                "user_id": user["user_id"],
                "endpoint": "/v1/chat/completions",
                "model": model,
                "status": "error",
                "status_code": resp.status_code,
                "upstream_status": resp.status_code,
                "latency_ms": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "tokens_total": 0,
                "cost_usd": 0.0,
                "image_count": None,
                "tts_chars": None,
                "stt_seconds": None,
                "video_count": None,
                "error_type": "upstream_error",
                "error_message": truncate_text(error_text, 500)
            })
            
            remove_pending(request_id)
            try:
                await resp.aclose()
            finally:
                await client.aclose()
        logger.warning("stream_error rid=%s status=%s body=%s", request_id, resp.status_code, error_text[:500])
        raise HTTPException(resp.status_code, error_text)

    async def _iter_bytes():
        sampled: bytearray = bytearray()
        usage_data = None  # Track usage from stream_options.include_usage
        
        try:
            async for chunk in resp.aiter_bytes():
                if len(sampled) < 8192:
                    sampled.extend(chunk[: max(0, 8192 - len(sampled))])
                
                # Try to extract usage from SSE data (stream_options.include_usage)
                try:
                    chunk_str = chunk.decode("utf-8", errors="ignore")
                    if chunk_str.startswith("data: ") and not chunk_str.startswith("data: [DONE]"):
                        json_str = chunk_str[6:].strip()
                        if json_str:
                            chunk_data = json.loads(json_str)
                            # Extract usage from final chunk
                            if "usage" in chunk_data:
                                usage_data = chunk_data["usage"]
                except Exception:
                    pass  # Ignore parsing errors
                
                yield chunk
        except (httpx.StreamClosed, httpx.RemoteProtocolError, asyncio.CancelledError):
            return
        finally:
            # Finalize streaming: reconcile usage and bump quota
            await _finalize_streaming(request, user, model, request_id, usage_data)
            
            remove_pending(request_id)
            try:
                await resp.aclose()
            finally:
                await client.aclose()
            logger.info("stream_end rid=%s", request_id)
            if sampled:
                detail_log(
                    "chat.stream.sample",
                    request=request,
                    rid=request_id,
                    user_id=user.get("user_id"),
                    sample_bytes=len(sampled),
                    sample=truncate_text(sampled.decode("utf-8", errors="ignore"), limit=4000),
                )

    return StreamingResponse(
        _iter_bytes(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id,
        },
    )


async def _handle_non_streaming(request: Request, user: dict, model: str, body: dict, headers: dict, request_id: str, limit_tokens: int, used_tokens: int, limit_cost: float, used_cost: float):
    """Handle non-streaming chat completions"""
    client: httpx.AsyncClient = request.app.state.http_client
    detail_log(
        "upstream.request",
        request=request,
        rid=request_id,
        user_id=user.get("user_id"),
        upstream=f"{LITELLM_BASE}/chat/completions",
        method="POST",
        headers=safe_headers(headers),
        body=body,
    )
    resp = await client.post(f"{LITELLM_BASE}/chat/completions", headers=headers, json=body)
    if resp.status_code >= 400:
        try:
            raise HTTPException(resp.status_code, resp.json())
        except Exception:
            raise HTTPException(resp.status_code, resp.text)
    data = resp.json()
    try:
        content_preview = (((data.get("choices") or [{}])[0].get("message") or {}).get("content"))
    except Exception:
        content_preview = None
    detail_log(
        "chat.response",
        request=request,
        rid=request_id,
        user_id=user.get("user_id"),
        status=resp.status_code,
        model=model,
        content=truncate_text(content_preview, limit=2000),
        usage=data.get("usage"),
    )
    litellm_cost = get_cost_from_headers(resp.headers)

    usage = data.get("usage", {}) or {}
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
    
    # Load prices for cost calculation
    from core.cost import load_prices
    prices = load_prices()
    cost_usd = litellm_cost if litellm_cost > 0 else calc_cost_usd(model, prompt_tokens, completion_tokens, prices)
    
    # Set usage state for audit (BEFORE quota check - will be logged even if quota fails)
    set_usage_state(request, prompt_tokens, completion_tokens, total_tokens, cost_usd)

    if limit_tokens > 0 and used_tokens + total_tokens > limit_tokens:
        set_error_state(request, "quota", f"Token quota exceeded")
        raise HTTPException(403, f"Token quota exceeded for {user['user_id']} ({used_tokens + total_tokens}/{limit_tokens})")
    if limit_cost > 0 and used_cost + cost_usd > limit_cost + 1e-9:
        set_error_state(request, "quota", f"Cost quota exceeded")
        raise HTTPException(403, f"Cost quota exceeded for {user['user_id']} (${used_cost + cost_usd:.2f}/${limit_cost:.2f})")

    enforce_and_bump_quota(user["user_id"], add_tokens=total_tokens, add_cost_usd=cost_usd)

    data["_mw_user"] = user["user_id"]
    data["_mw_request_id"] = request_id
    data["_mw_added_tokens"] = total_tokens
    data["_mw_added_cost_usd"] = round(cost_usd, 6)

    return JSONResponse(status_code=200, content=data)
