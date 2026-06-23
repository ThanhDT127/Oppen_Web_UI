"""
title: Tool Approval Handler Filter
author: Antigravity
description: Intercepts /approve and /reject commands, updates status, and executes approved actions.
version: 1.0.0
type: filter
requirements: requests
"""

import logging
import re
import requests
from typing import Optional
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Filter:
    class Valves(BaseModel):
        middleware_url: str = Field(
            default="http://middleware:5000/v1",
            description="Base URL of the Middleware API (internal container address)"
        )
        admin_token: str = Field(
            default="YOUR_SUBKEY_ADMIN",
            description="Admin key for authenticating with the Middleware API"
        )

    def __init__(self):
        self.valves = self.Valves()

    async def inlet(self, body: dict, __user__: dict = None) -> dict:
        """
        Intercepts incoming user prompts before they reach the LLM.
        Detects `/approve` and `/reject` commands.
        """
        logger.info("=== Tool Approval Filter: inlet() called ===")
        
        messages = body.get("messages", [])
        if not messages or not __user__:
            return body

        last_msg = messages[-1]
        content = last_msg.get("content", "")
        if not isinstance(content, str):
            return body

        # Match /approve or /reject commands
        content_stripped = content.strip()
        match = re.match(r"^/(approve|reject)\s+([a-zA-Z0-9_-]+)$", content_stripped)
        if not match:
            return body

        cmd = match.group(1)      # "approve" or "reject"
        action_id = match.group(2)
        user_id = __user__.get("id", "")

        logger.info("Intercepted command: /%s for action %s by user %s", cmd, action_id, user_id)

        # Call Middleware to update status
        status_url = f"{self.valves.middleware_url.rstrip('/')}/_mw/approvals/{action_id}/status"
        headers = {
            "Authorization": f"Bearer {self.valves.admin_token}"
        }
        status_val = "approved" if cmd == "approve" else "rejected"

        try:
            # 1. Update approval status in Middleware
            res = requests.post(status_url, headers=headers, json={"status": status_val}, timeout=10)
            if res.status_code != 200:
                last_msg["content"] = f"[SYSTEM: Lỗi cập nhật trạng thái Middleware: {res.text[:200]}]"
                return body

            if cmd == "reject":
                last_msg["content"] = f"[SYSTEM: Người dùng từ chối phê duyệt hành động {action_id}. Vui lòng thông báo cho người dùng rằng hành động này đã bị hủy bỏ theo ý của họ.]"
                return body

            # 2. Get details for execution
            get_url = f"{self.valves.middleware_url.rstrip('/')}/_mw/approvals/{action_id}"
            res_details = requests.get(get_url, headers=headers, timeout=10)
            if res_details.status_code != 200:
                last_msg["content"] = f"[SYSTEM: Không tìm thấy chi tiết hành động: {res_details.text[:200]}]"
                return body

            approval_data = res_details.json()
            tool_name = approval_data.get("tool_name")
            payload = approval_data.get("payload", {})

            # 3. Execute approved action
            if tool_name == "google_gmail_tool":
                recipient = payload.get("recipient")
                subject = payload.get("subject")
                mail_body = payload.get("body")

                # Fetch user OAuth token via integrations API
                token_url = f"{self.valves.middleware_url.rstrip('/')}/_mw/integrations/get_token"
                token_params = {
                    "provider": "google_gmail",
                    "openwebui_user_id": user_id
                }
                res_token = requests.get(token_url, headers=headers, params=token_params, timeout=10)
                
                if res_token.status_code != 200:
                    last_msg["content"] = f"[SYSTEM: Phê duyệt thành công, nhưng không lấy được Gmail OAuth token từ Middleware: {res_token.text[:200]}]"
                    return body
                
                token_data = res_token.json()
                access_token = token_data.get("access_token")
                if not access_token:
                    last_msg["content"] = "[SYSTEM: Gmail access token bị rỗng từ Middleware.]"
                    return body
                
                # Call Gmail API to send email
                import base64
                from email.mime.text import MIMEText
                
                gmail_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
                gmail_headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                message = MIMEText(mail_body)
                message["to"] = recipient
                message["subject"] = subject
                raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
                
                res_gmail = requests.post(
                    gmail_url,
                    headers=gmail_headers,
                    json={"raw": raw_message},
                    timeout=15
                )
                
                if res_gmail.status_code == 200:
                    res_json = res_gmail.json()
                    last_msg["content"] = (
                        f"[SYSTEM: Hành động đã được phê duyệt và thực hiện thành công. "
                        f"Kết quả gửi Gmail: Gửi email thành công tới {recipient} (Message ID: {res_json.get('id')}). "
                        f"Hãy xác nhận thành công này cho người dùng một cách ngắn gọn, tự nhiên.]"
                    )
                else:
                    last_msg["content"] = (
                        f"[SYSTEM: Hành động đã được phê duyệt nhưng gọi Gmail API thất bại với mã {res_gmail.status_code}: {res_gmail.text[:200]}. "
                        f"Hãy báo lỗi này cho người dùng.]"
                    )
            else:
                last_msg["content"] = f"[SYSTEM: Hành động đã được phê duyệt nhưng filter không hỗ trợ thực thi công cụ '{tool_name}'.]"

        except Exception as e:
            logger.error("Error processing filter approval: %s", str(e))
            last_msg["content"] = f"[SYSTEM: Lỗi hệ thống trong quá trình phê duyệt: {str(e)}]"

        return body
