## Why

Khi user hết quota giữa lúc chat (streaming), middleware raise HTTPException 403 **SAU** khi LLM đã trả response. Lúc này stream đã close → UI treo, user không nhận được thông báo gì. Cần cho phép request cuối hoàn thành + inject thông báo hết quota rõ ràng.

## What Changes

- **Pre-check quota TRƯỚC khi gọi LLM**: Kiểm tra quota trước. Nếu đã vượt 100% → KHÔNG gọi LLM, trả thông báo hết quota trực tiếp (giả lập response).
- **Fake response khi hết quota**: Tạo 1 response giả với nội dung thông báo hết quota kèm thông tin reset period (tháng/tuần, còn X ngày).
- **Post-check vẫn giữ**: Sau khi LLM response, vẫn check quota. Nếu vượt sau request này → inject warning nhưng KHÔNG raise exception.
- **Thông báo hết quota**: "🔒 Bạn đã sử dụng hết quota [tháng/tuần] này. Quota tiếp theo sẽ reset trong X ngày."

## Impact

- **`llm-mw/api/chat.py`**: Thêm pre-check trước khi gọi LLM. Sửa post-check không raise 403 nữa mà inject warning.
- **`llm-mw/core/quota.py`**: Thêm function `get_quota_reset_info()` để tính ngày reset.
- **Không ảnh hưởng**: LiteLLM, Open WebUI, PostgreSQL, SearXNG.
