"""
Notification API endpoints for the dashboard.
"""

from fastapi import Request, Query
from fastapi.responses import JSONResponse

from config import logger
from core.notification import get_notifications, get_unread_count, mark_as_read
from utils.auth_guard import require_admin_or_session


async def list_notifications(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    unread: bool = Query(False),
):
    """
    GET /v1/_mw/admin/notifications

    List notifications (newest first). Admin only (cookie or header).
    """
    require_admin_or_session(request)

    items = get_notifications(limit=limit, unread_only=unread)
    return JSONResponse(content={"notifications": items, "count": len(items)})


async def unread_count(request: Request):
    """
    GET /v1/_mw/admin/notifications/unread

    Get count of unread notifications. Admin only (cookie or header).
    """
    require_admin_or_session(request)

    count = get_unread_count()
    return JSONResponse(content={"unread": count})


async def mark_notification_read(request: Request, notif_id: int):
    """
    POST /v1/_mw/admin/notifications/{notif_id}/read

    Mark a single notification as read. Admin only (cookie or header).
    """
    require_admin_or_session(request)

    ok = mark_as_read(notif_id=notif_id)
    if ok:
        return JSONResponse(content={"status": "ok"})
    return JSONResponse(status_code=500, content={"error": "Failed to mark as read"})


async def mark_all_read(request: Request):
    """
    POST /v1/_mw/admin/notifications/read-all

    Mark all notifications as read. Admin only (cookie or header).
    """
    require_admin_or_session(request)

    ok = mark_as_read(all=True)
    if ok:
        return JSONResponse(content={"status": "ok", "message": "All notifications marked as read"})
    return JSONResponse(status_code=500, content={"error": "Failed to mark all as read"})

