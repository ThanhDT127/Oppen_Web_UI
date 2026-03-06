"""
Models endpoint for listing available LLM models.
"""

from fastapi import Request
import httpx

from config import LITELLM_BASE, LITELLM_KEY, RESTRICTED_MODELS
from core.auth import require_user
from utils.helpers import env_truthy
from utils.logging import detail_log


async def list_models(request: Request):
    """
    List available models from LiteLLM.
    Filters out restricted models unless MW_EXPOSE_RESTRICTED_MODELS is enabled.
    """
    user = require_user(request)
    
    try:
        client: httpx.AsyncClient = request.app.state.http_client
        detail_log(
            "models.request",
            request=request,
            user_id=user.get("user_id"),
        )
        resp = await client.get(
            f"{LITELLM_BASE}/models",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            timeout=10,
        )
        if resp.status_code == 200:
            payload = resp.json() or {}
            data = payload.get("data")
            if isinstance(data, list):
                # Get user's allowed models
                allowed_models = user.get("allowed_models", ["*"])
                allow_all = allowed_models == ["*"]
                
                filtered = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    mid = item.get("id") or item.get("model") or item.get("name")
                    
                    # Filter restricted models
                    if not env_truthy("MW_EXPOSE_RESTRICTED_MODELS", default=False):
                        if isinstance(mid, str) and mid in RESTRICTED_MODELS:
                            continue
                    
                    # Filter by user's allowed_models
                    if not allow_all and isinstance(mid, str):
                        if mid not in allowed_models:
                            continue
                    
                    filtered.append(item)
                payload["data"] = filtered
            return payload
        return {"data": []}
    except Exception:
        # Fallback to empty list if LiteLLM is down
        return {"data": []}
