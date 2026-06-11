"""
Docling Proxy — Intercepts document extraction and materializes images.
This ensures Open WebUI stores clean Markdown with material URLs in its vector DB.
"""

import os
import re
import httpx
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse

from config import logger
from utils.media import maybe_materialize_data_url

# The actual docling-serve internal URL
REAL_DOCLING_URL = os.getenv("REAL_DOCLING_URL", "http://docling:5001").rstrip("/")


async def docling_proxy(request: Request):
    """
    Catch-all proxy for Docling requests.
    Supports GET /health and POST /convert (the main endpoint).
    """
    path = request.url.path
    # Strip the '/docling-proxy' prefix to get the sub-path
    target_subpath = path.replace("/docling-proxy", "")
    if not target_subpath:
        target_subpath = "/"
    
    target_url = f"{REAL_DOCLING_URL}{target_subpath}"
    
    method = request.method
    headers = dict(request.headers)
    # Host header must be updated to the internal service name
    headers.pop("host", None)
    
    content = await request.body()
    params = dict(request.query_params)

    logger.info("docling_proxy: %s %s -> %s", method, path, target_url)

    try:
        client: httpx.AsyncClient = request.app.state.http_client
        resp = await client.request(
            method,
            target_url,
            headers=headers,
            content=content,
            params=params,
            timeout=300.0 # Document conversion can be slow
        )
    except Exception as e:
        logger.error("docling_proxy_error: %s", e)
        raise HTTPException(502, f"Error connecting to Docling service: {e}")

    # --- Response Interception & Materialization ---
    if resp.status_code == 200 and "application/json" in resp.headers.get("content-type", ""):
        try:
            data = resp.json()
            modified = False
            
            # Debug: Log all keys to find where images might be hiding
            logger.info("docling_proxy: response keys: %s", list(data.keys()))
            doc_obj = data.get("document", {})
            if isinstance(doc_obj, dict):
                logger.info("docling_proxy: document keys: %s", list(doc_obj.keys()))
            
            # 1. Check for images in md_content
            markdown_content = doc_obj.get("md_content") if isinstance(doc_obj, dict) else None
            
            if isinstance(markdown_content, str):
                logger.info("docling_proxy: md_content length: %d", len(markdown_content))
                if "data:image/" in markdown_content:
                    logger.info("docling_proxy: materializing images found in md_content")
                    
                    start_search = 0
                    while True:
                        idx = markdown_content.find("data:image/", start_search)
                        if idx == -1:
                            break
                        
                        end_idx = len(markdown_content)
                        for char in [" ", "'", "\"", ")", "]", "}", "\n", "\t", "\\", ">"]:
                            term_idx = markdown_content.find(char, idx)
                            if term_idx != -1 and term_idx < end_idx:
                                end_idx = term_idx
                        
                        data_url = markdown_content[idx:end_idx].strip()
                        data_url = data_url.rstrip(".,;)]}>\\")
                        
                        if ";base64," in data_url:
                            try:
                                public_url = maybe_materialize_data_url(request, url=data_url)
                                if public_url != data_url:
                                    markdown_content = markdown_content[:idx] + public_url + markdown_content[end_idx:]
                                    logger.info("docling_proxy: materialized base64 -> %s", public_url)
                                    modified = True
                                    start_search = idx + len(public_url)
                                else:
                                    start_search = idx + len(data_url)
                            except Exception as e:
                                logger.error("docling_proxy_materialize_err: %s", e)
                                start_search = idx + len(data_url)
                        else:
                            start_search = idx + len(data_url)
                    
                    if modified:
                        data["document"]["md_content"] = markdown_content
                else:
                    # Check if images are in a separate field (e.g. data['document']['images'])
                    images_list = doc_obj.get("images", []) if isinstance(doc_obj, dict) else []
                    if images_list:
                        logger.info("docling_proxy: found %d images in separate 'images' field", len(images_list))
                        # Note: stitching images back to MD requires knowing their placeholders. 
                        # For now, we just log their presence.
                    else:
                        logger.info("docling_proxy: NO images found in md_content or images field")
            
            if modified:
                return JSONResponse(content=data)
        except Exception as e:
            logger.error("docling_proxy_interception_fail: %s", e)
            pass

    # Default: proxy the response as-is
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers)
    )
