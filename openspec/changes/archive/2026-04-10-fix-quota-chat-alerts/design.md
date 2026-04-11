## Context

Middleware xử lý quota theo flow: `require_user()` → `enforce_and_bump_quota()` → `check_and_send_alerts()`. Dashboard notifications hoạt động tốt (xác nhận qua screenshots). Vấn đề chỉ nằm ở phía **chat response** — user không thấy gì.

Hiện tại có 2 cơ chế cảnh báo quota đến user:
1. **Filter Function** (`quota_alert_filter.py`): Open WebUI outlet filter gọi `/v1/_mw/quota-status` sau mỗi response, thêm warning vào cuối → **chưa hoạt động** (chưa rõ đã register hay chưa, user_id mapping có thể sai)
2. **HTTPException 403**: Khi hết quota → raise 403 → Open WebUI hiển thị error box đỏ rỗng (chỉ có icon `⊘`, không có text)

## Goals / Non-Goals

**Goals:**
- Inject cảnh báo quota trực tiếp vào response chat từ **middleware level** (không phụ thuộc Filter)
- Trả error message rõ ràng, tiếng Việt khi quota exceeded (403)
- Fix Filter Function để hoạt động đúng (backup mechanism)
- Đảm bảo cảnh báo hiển thị cả streaming và non-streaming

**Non-Goals:**  
- Không thay đổi dashboard notifications (đã hoạt động tốt)
- Không thay đổi email alerts
- Không thay đổi quota calculation logic

## Decisions

### D1: Inject quota warning vào response tại middleware level

**Decision**: Thêm logic vào `_handle_non_streaming()` và `_finalize_streaming()` trong `chat.py` để append quota warning vào nội dung response của LLM khi user ≥ 80% quota.

**Rationale**: Filter Function phụ thuộc vào Open WebUI registration — nếu chưa register hoặc register lỗi thì không chạy. Middleware-level injection đảm bảo hoạt động 100% vì code nằm trong middleware.

**Alternative considered**: Chỉ fix Filter Function → rejected vì không đáng tin cậy (phụ thuộc admin register đúng).

### D2: Quota exceeded trả JSON detail

**Decision**: Khi raise HTTPException 403, trả body JSON format:
```json
{
  "detail": "⚠️ Bạn đã hết quota tháng này ($10.00/$10.00). Vui lòng liên hệ admin.",
  "error_code": "QUOTA_EXCEEDED",
  "quota_info": {"used": 10.0, "limit": 10.0, "percent": 100}
}
```

Với streaming: inject SSE chunk cuối cùng chứa message cảnh báo trước khi gửi error.

**Rationale**: Open WebUI hiển thị `detail` field trong error box → user sẽ thấy message rõ ràng.

### D3: Streaming quota warning = extra SSE chunk

**Decision**: Sau khi stream hoàn tất và `_finalize_streaming()` tính xong cost, nếu user ≥80% quota, gửi thêm 1 SSE chunk chứa text cảnh báo vào cuối response.

**Risk**: Stream đã close khi finalize chạy → không thể append. **Mitigation**: Kiểm tra quota TRƯỚC khi stream (pre-check) dựa trên current usage, và inject warning vào stream nếu cần.

## Risks / Trade-offs

- **[Duplicate warnings]** → Mitigation: Nếu middleware đã inject, Filter sẽ thấy warning text đã có → skip (hoặc disable Filter).
- **[Streaming complexity]** → Mitigation: Pre-check quota trước stream, post-check sau finalize. Nếu quota vượt ngưỡng trong lúc stream, warning sẽ hiện ở response tiếp theo.
