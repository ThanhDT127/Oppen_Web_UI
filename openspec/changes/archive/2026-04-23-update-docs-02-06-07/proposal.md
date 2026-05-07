## Why

Ba tài liệu kỹ thuật (02-tai-lieu-van-hanh, 06-rag-architecture, 07-api-reference) đang chứa thông tin lỗi thời hoặc sai lệch so với hệ thống đang chạy thực tế (docker-compose.yml, main.py, litellm_config.yaml). Cần đồng bộ để tránh sai sót vận hành.

## What Changes

- **DOC-02** (`02-tai-lieu-van-hanh.md`): Sửa sai route reconcile trong section 3.4, cập nhật module list Middleware (section 1.3) gồm các module mới (notifications, quota_status, auth_check, auth_test, services/), sửa API CRUD user section 6.3 dùng route `/v1/_mw/dashboard/login` thay vì `/dashboard/login`
- **DOC-06** (`06-rag-architecture.md`): Sửa chunk_size/overlap trong code example (1000/200 → 1500/100 như docker-compose), sửa `vector(384)` → `vector(1536)` trong retrieval flow diagram
- **DOC-07** (`07-api-reference.md`): Sửa dashboard login/logout routes (`/dashboard/login` → `/v1/_mw/dashboard/login`), cập nhật schema phản hồi `/v1/_mw/summary` với các trường mới (pending_open_count, embedding_calls, video_calls, billable_calls, nonbillable_calls, usage_missing_calls), bổ sung các endpoints thiếu (/v1/embeddings, /v1/_mw/quota-status, /v1/_mw/audit/query, /v1/_mw/admin/notifications, /v1/_mw/admin/alerts/config), sửa mô tả Rate Limit (quota là cost USD không phải request count)

## Capabilities

### New Capabilities
- `doc-corrections`: Chỉnh sửa thông tin sai lệch trong nội dung tài liệu kỹ thuật hiện có

### Modified Capabilities
<!-- Không có spec-level behavior changes trong codebase — đây là documentation-only update -->

## Impact

- Chỉ ảnh hưởng đến 3 file Markdown trong `docs/`
- Không thay đổi source code, config, hoặc database
- Không breaking changes
