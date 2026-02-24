"""
Media handling utilities for file uploads and serving.
"""

import os
import re
import uuid
import base64
from typing import Any
from fastapi import Request, HTTPException
from fastapi.responses import Response

from config import MW_MEDIA_DIR


def mime_to_ext(mime: str) -> str:
    """
    Convert MIME type to file extension.
    
    Args:
        mime: MIME type string
        
    Returns:
        File extension (without dot)
    """
    m = (mime or "").lower().strip()
    
    # Images
    if m == "image/png":
        return "png"
    if m in ("image/jpeg", "image/jpg"):
        return "jpg"
    if m == "image/webp":
        return "webp"
    if m == "image/gif":
        return "gif"
    if m == "image/svg+xml":
        return "svg"
    
    # Documents
    if m == "application/pdf":
        return "pdf"
    if m in ("application/msword", "application/vnd.ms-word"):
        return "doc"
    if m == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return "docx"
    if m in ("application/vnd.ms-excel", "application/excel"):
        return "xls"
    if m == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        return "xlsx"
    if m in ("application/vnd.ms-powerpoint", "application/powerpoint"):
        return "ppt"
    if m == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
        return "pptx"
    
    # Text & Data
    if m == "text/plain":
        return "txt"
    if m == "text/csv":
        return "csv"
    if m in ("application/json", "text/json"):
        return "json"
    if m in ("application/xml", "text/xml"):
        return "xml"
    if m == "text/markdown":
        return "md"
    if m == "text/html":
        return "html"
    
    # Code files
    if m == "text/x-python":
        return "py"
    if m in ("application/javascript", "text/javascript"):
        return "js"
    if m == "text/x-java":
        return "java"
    if m in ("text/x-c", "text/x-c++"):
        return "cpp"
    
    # Archives
    if m == "application/zip":
        return "zip"
    if m in ("application/x-rar-compressed", "application/x-rar"):
        return "rar"
    if m in ("application/x-7z-compressed", "application/x-7z"):
        return "7z"
    
    return "bin"


def save_bytes_to_media(data: bytes, *, mime: str) -> str:
    """
    Save bytes to media directory with unique filename.
    
    Args:
        data: File bytes
        mime: MIME type
        
    Returns:
        Filename (UUID.ext)
    """
    ext = mime_to_ext(mime)
    name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(MW_MEDIA_DIR, name)
    with open(path, "wb") as f:
        f.write(data)
    return name


def public_media_url(request: Request, name: str) -> str:
    """
    Generate public URL for media file.
    
    Detection order:
    1. MW_PUBLIC_URL env var (recommended for production)
    2. X-Forwarded-Host / X-Forwarded-Proto headers (reverse proxy)
    3. Host header if not Docker-internal (e.g. 192.168.x.x:5000)
    4. Fallback: http://localhost:5000
    
    NOTE: request.base_url returns Docker internal hostname (e.g. http://middleware:5000/)
    which is NOT accessible from the browser. We must use the externally accessible URL.
    """
    # 1. Explicit env var (best option)
    public_base = os.environ.get("MW_PUBLIC_URL", "").rstrip("/")
    if public_base:
        return f"{public_base}/v1/_mw/media/{name}"
    
    # 2. Reverse proxy headers
    fwd_host = request.headers.get("x-forwarded-host")
    fwd_proto = request.headers.get("x-forwarded-proto", "http")
    if fwd_host:
        return f"{fwd_proto}://{fwd_host}/v1/_mw/media/{name}"
    
    # 3. Host header (skip Docker-internal names like "middleware")
    host = request.headers.get("host", "")
    docker_internal_names = {"middleware", "litellm", "open-webui", "postgres"}
    host_name = host.split(":")[0] if host else ""
    if host and host_name not in docker_internal_names:
        scheme = str(request.url.scheme) or "http"
        return f"{scheme}://{host}/v1/_mw/media/{name}"
    
    # 4. Last resort fallback
    port = request.url.port or 5000
    return f"http://localhost:{port}/v1/_mw/media/{name}"


def maybe_materialize_data_url(
    request: Request, 
    *, 
    url: str, 
    fallback_mime: str = "application/octet-stream"
) -> str:
    """
    Convert data: URL to public URL for any file type (images, documents, etc.).
    
    Args:
        request: FastAPI request
        url: URL to materialize (data: or regular URL)
        fallback_mime: MIME type to use if not specified in data URL
        
    Returns:
        Public URL or original URL if not a data URL
    """
    if not isinstance(url, str) or not url:
        return url
    if not url.startswith("data:"):
        return url

    # Format: data:<mime>;base64,<b64>
    try:
        header, b64 = url.split(",", 1)
        mime = fallback_mime
        m = re.match(r"^data:([^;]+);base64$", header)
        if m:
            mime = m.group(1)
        raw = base64.b64decode(b64)
        name = save_bytes_to_media(raw, mime=mime)
        return public_media_url(request, name)
    except Exception:
        return url


def maybe_materialize_image_url(
    request: Request, 
    *, 
    url: str, 
    fallback_mime: str = "image/png"
) -> str:
    """
    Legacy function for backward compatibility - now calls maybe_materialize_data_url.
    
    Args:
        request: FastAPI request
        url: Image URL to materialize
        fallback_mime: Default MIME type for images
        
    Returns:
        Public URL or original URL
    """
    return maybe_materialize_data_url(request, url=url, fallback_mime=fallback_mime)


def maybe_materialize_image_items(
    request: Request, 
    items: Any, 
    *, 
    fallback_mime: str = "image/png"
):
    """
    Materialize image items in a list (from OpenAI API responses).
    Modifies items in-place.
    
    Args:
        request: FastAPI request
        items: List of image items with url/b64_json
        fallback_mime: Default MIME type
    """
    if not isinstance(items, list):
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        b64 = item.get("b64_json")

        if isinstance(url, str) and url.startswith("data:"):
            item["url"] = maybe_materialize_image_url(request, url=url, fallback_mime=fallback_mime)
            continue

        if b64 and (not url):
            try:
                raw = base64.b64decode(b64)
                name = save_bytes_to_media(raw, mime=fallback_mime)
                item["url"] = public_media_url(request, name)
            except Exception:
                # Leave as-is; callers may still use b64_json.
                pass


def get_media_mime_type(ext: str) -> str:
    """
    Get MIME type for file extension.
    
    Args:
        ext: File extension (with or without dot)
        
    Returns:
        MIME type string
    """
    ext = ext.lower().lstrip(".")
    
    # Comprehensive MIME type mapping
    mime_map = {
        # Images
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
        "svg": "image/svg+xml",
        
        # Documents
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        
        # Text & Data
        "txt": "text/plain",
        "csv": "text/csv",
        "json": "application/json",
        "xml": "application/xml",
        "md": "text/markdown",
        "html": "text/html",
        
        # Code
        "py": "text/x-python",
        "js": "application/javascript",
        "java": "text/x-java",
        "cpp": "text/x-c++",
        
        # Archives
        "zip": "application/zip",
        "rar": "application/x-rar-compressed",
        "7z": "application/x-7z-compressed",
    }
    
    return mime_map.get(ext, "application/octet-stream")


def get_allowed_extensions_pattern() -> str:
    """
    Get regex pattern for allowed file extensions.
    
    Returns:
        Regex pattern string for file extensions
    """
    return (
        "png|jpg|jpeg|webp|gif|svg|"  # Images
        "pdf|doc|docx|xls|xlsx|ppt|pptx|"  # Documents
        "txt|csv|json|xml|md|html|"  # Text/Data
        "py|js|java|cpp|"  # Code
        "zip|rar|7z|"  # Archives
        "bin"  # Binary fallback
    )
