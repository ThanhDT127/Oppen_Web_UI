"""
Media serving endpoint for uploaded files.
"""

import os
import re
from fastapi import HTTPException
from fastapi.responses import Response

from config import MW_MEDIA_DIR
from utils.media import get_allowed_extensions_pattern, get_media_mime_type


async def serve_media(name: str):
    """
    Serve uploaded media files (images, documents, etc.).
    Files are validated against allowed extensions pattern.
    """
    # Constrain to our generated filenames - now supports many extensions
    allowed_extensions = get_allowed_extensions_pattern()
    pattern = rf"[a-f0-9]{{32}}\.({allowed_extensions})"
    if not re.fullmatch(pattern, name, flags=re.IGNORECASE):
        raise HTTPException(404, "Not found")
    
    path = os.path.join(MW_MEDIA_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(404, "Not found")

    ext = name.rsplit(".", 1)[-1].lower()
    mime = get_media_mime_type(ext)
    
    with open(path, "rb") as f:
        data = f.read()
    
    return Response(
        content=data, 
        media_type=mime, 
        headers={"Cache-Control": "public, max-age=31536000"}
    )
