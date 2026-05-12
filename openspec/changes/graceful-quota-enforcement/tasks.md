# Tasks — graceful-quota-enforcement

## Core Logic
- [x] 1. Thêm `get_quota_reset_info(user)` vào `core/quota.py` ✅
- [x] 2. Thêm pre-check quota TRƯỚC khi gọi LLM trong `api/chat.py` ✅
- [x] 3. Tạo fake response khi quota đã vượt 100% (streaming + non-streaming) ✅
- [x] 4. Sửa post-check: không raise 403 nữa, log warning thay vì crash ✅

## Testing
- [x] 5. Test pre-check block: hết quota → nhận thông báo rõ ràng, không treo ✅
- [x] 6. Test period info: hiển thị đúng "tháng" + "19 ngày" ✅
- [x] 7. Test streaming: SSE format đúng, UI render OK ✅

## Deploy
- [x] 8. Docker build + restart ✅
