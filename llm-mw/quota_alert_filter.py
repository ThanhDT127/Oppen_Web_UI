"""
title: Quota Alert Filter
author: LLM Gateway Admin
description: Hiển thị cảnh báo quota cho user khi sử dụng ≥80% trong mỗi response chat.
version: 1.0.0
type: filter
"""

from pydantic import BaseModel, Field
import requests
from typing import Optional


class Filter:
    """
    Filter này chạy SAU KHI nhận response từ LLM (outlet).
    Gọi Middleware API kiểm tra % quota đã dùng.
    Nếu ≥80% → thêm dòng cảnh báo vào cuối response.
    """

    class Valves(BaseModel):
        middleware_url: str = Field(
            default="http://host.docker.internal:5000",
            description="URL của Middleware server (mặc định cho Docker)"
        )
        enabled: bool = Field(
            default=True,
            description="Bật/tắt cảnh báo quota"
        )
        warning_threshold: int = Field(
            default=80,
            description="Ngưỡng cảnh báo vàng (%) - mặc định 80%"
        )
        critical_threshold: int = Field(
            default=95,
            description="Ngưỡng cảnh báo đỏ (%) - mặc định 95%"
        )

    def __init__(self):
        self.valves = self.Valves()

    async def outlet(self, body: dict, __user__: dict = None) -> dict:
        """
        Chạy SAU KHI nhận response từ LLM.
        Kiểm tra quota và thêm cảnh báo nếu cần.
        """
        # Skip nếu disabled hoặc không có user
        if not self.valves.enabled or not __user__:
            return body

        # Skip nếu không có messages
        messages = body.get("messages", [])
        if not messages:
            return body

        try:
            # Lấy user_id từ Open WebUI user info
            user_id = __user__.get("id", "") or __user__.get("email", "")
            if not user_id:
                return body

            # Gọi Middleware API kiểm tra quota (timeout ngắn, không block)
            resp = requests.get(
                f"{self.valves.middleware_url}/v1/_mw/quota-status",
                params={"user_id": user_id},
                timeout=2
            )

            if resp.status_code != 200:
                return body

            data = resp.json()

            # Bỏ qua nếu user không giới hạn hoặc không tìm thấy
            if not data.get("found") or data.get("unlimited"):
                return body

            percent = data.get("percent_used", 0)
            remaining = data.get("remaining_usd", 0)

            # Thêm cảnh báo vào cuối response
            alert_text = None

            if percent >= self.valves.critical_threshold:
                alert_text = (
                    f"\n\n---\n"
                    f"🔴 **Cảnh báo quota**: Bạn đã sử dụng "
                    f"**{percent:.0f}%** quota tháng này "
                    f"(còn ~${remaining:.2f}). "
                    f"Vui lòng liên hệ admin nếu cần tăng quota."
                )
            elif percent >= self.valves.warning_threshold:
                alert_text = (
                    f"\n\n---\n"
                    f"⚠️ Bạn đã sử dụng "
                    f"**{percent:.0f}%** quota tháng này "
                    f"(còn ~${remaining:.2f})."
                )

            if alert_text and messages:
                # Thêm vào message cuối cùng (response của LLM)
                last_msg = messages[-1]
                if isinstance(last_msg.get("content"), str):
                    last_msg["content"] += alert_text

        except requests.exceptions.Timeout:
            pass  # Timeout → bỏ qua, không block response
        except requests.exceptions.ConnectionError:
            pass  # MW không chạy → bỏ qua
        except Exception:
            pass  # Bất kỳ lỗi nào → bỏ qua, không block user

        return body
