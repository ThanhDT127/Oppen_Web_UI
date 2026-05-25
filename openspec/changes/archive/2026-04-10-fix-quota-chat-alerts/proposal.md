## Why

Khi user gần hết hoặc hết quota, hệ thống chỉ hiển thị cảnh báo trên dashboard (notifications) nhưng **không** có cảnh báo nào hiển thị trong chat cho user. Cụ thể:

1. **Filter `quota_alert_filter.py`** đã được thiết kế để thêm cảnh báo vào mỗi response chat khi user ≥80% quota, nhưng filter này có thể chưa hoạt động đúng do: (a) chưa được đăng ký trong Open WebUI Functions, hoặc (b) user_id mapping giữa Open WebUI và middleware sai.

2. **Khi hết sạch quota** (100%), middleware trả HTTP 403 nhưng Open WebUI hiển thị lỗi generic (red box rỗng) — user không biết lý do bị chặn, không biết cần làm gì.

## What Changes

- Cải thiện error response khi quota exceeded: trả JSON rõ ràng với message tiếng Việt mô tả tình trạng quota
- Thêm inline quota warning trực tiếp vào streaming response tại middleware level (không phụ thuộc Filter Function)
- Kiểm tra và fix logic của `quota_alert_filter.py` — đảm bảo nó map đúng user_id
- Thêm endpoint `/v1/_mw/quota-status` hỗ trợ auth via Bearer token (không chỉ query param)

## Capabilities

### New Capabilities
- `chat-quota-inline`: Middleware tự inject cảnh báo quota vào cuối streaming/non-streaming response khi user vượt ngưỡng, đồng thời trả error message rõ ràng khi hết quota hoàn toàn.

### Modified Capabilities
_(Không có specs tồn tại để modify)_

## Impact

- **Code affected**: `llm-mw/api/chat.py` (quota exceeded error messages + inline warning injection), `llm-mw/quota_alert_filter.py` (fix user_id mapping), `llm-mw/api/quota_status.py` (support Bearer auth)
- **APIs**: Modified `POST /v1/chat/completions` response format khi quota exceeded (403 trả JSON chi tiết hơn)
- **Dependencies**: Không thêm dependency mới
- **Systems**: Middleware container cần rebuild
