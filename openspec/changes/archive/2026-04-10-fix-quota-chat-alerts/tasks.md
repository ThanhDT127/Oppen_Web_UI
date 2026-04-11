## 1. Quota Exceeded Error Messages

- [x] 1.1 Sửa `enforce_and_bump_quota()` trong `core/quota.py` — trả error message tiếng Việt rõ ràng khi cost/token quota exceeded, bao gồm thông tin used/limit
- [x] 1.2 Sửa quota check trong `_handle_non_streaming()` (`api/chat.py`) — trả JSON detail message tiếng Việt thay vì message generic

## 2. Non-Streaming Quota Warning Injection

- [x] 2.1 Thêm helper function `_get_quota_warning_text()` trong `api/chat.py` — tính % quota và tạo warning text khi ≥80%
- [x] 2.2 Inject quota warning vào cuối response content trong `_handle_non_streaming()` sau khi bump quota thành công

## 3. Streaming Quota Warning Injection

- [x] 3.1 Thêm quota warning SSE chunks vào cuối stream trong `_iter_with_quota_warning()` — sau khi finalize tính cost xong, yield thêm warning chunk trước [DONE]
- [x] 3.2 Thêm pre-check quota trước khi bắt đầu stream — nếu đã 100% thì trả 403 ngay

## 4. Filter Function Fix

- [x] 4.1 Cập nhật `quota_alert_filter.py` v2.0 — thêm handling cho trường hợp 100% quota (exhausted message) + skip duplicate
- [x] 4.2 Đảm bảo filter không inject duplicate khi middleware đã inject warning (marker detection)

## 5. Testing & Verification

- [ ] 5.1 Build và deploy middleware
- [ ] 5.2 Test chat khi quota ≥80% — verify warning hiển thị trong chat
- [ ] 5.3 Test chat khi quota hết (100%) — verify error message rõ ràng
