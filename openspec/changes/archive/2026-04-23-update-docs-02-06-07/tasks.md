## 1. DOC-02: Tài liệu Vận hành

- [x] 1.1 Sửa module list Middleware (Section 1.3) — thêm notifications.py, quota_status.py, auth_check.py, auth_test.py và thư mục services/
- [x] 1.2 Sửa route reconcile thủ công (Section 3.4) từ `/v1/_mw/admin/reconcile` → `/admin/reconcile`
- [x] 1.3 Sửa route reconcile trong curl example (Section 3.4)
- [x] 1.4 Sửa API user admin (Section 6.3): cập nhật ghi chú dashboard login từ `/dashboard/login` → `/v1/_mw/dashboard/login`

## 2. DOC-06: Kiến trúc RAG

- [x] 2.1 Sửa code example chunk size/overlap (Section 2.2): `chunk_size = 1000, chunk_overlap = 200` → `chunk_size = 1500, chunk_overlap = 100`
- [x] 2.2 Cập nhật comment ví dụ chunking (Section 2.2) để phản ánh chunk_size=1500
- [x] 2.3 Sửa retrieval pipeline diagram (Section 5): `vector(384)` → `vector(1536)`

## 3. DOC-07: API Reference

- [x] 3.1 Sửa route Dashboard Login: `POST /dashboard/login` → `POST /v1/_mw/dashboard/login`
- [x] 3.2 Sửa route Dashboard Logout: `POST /dashboard/logout` → `POST /v1/_mw/dashboard/logout`
- [x] 3.3 Cập nhật schema phản hồi `/v1/_mw/summary` — thêm trường mới: `pending_open_count`, `embedding_calls`, `video_calls`, `billable_calls`, `nonbillable_calls`, `usage_missing_calls`
- [x] 3.4 Bổ sung section mới: `POST /v1/embeddings` (Tạo Embedding Vector)
- [x] 3.5 Bổ sung section mới: `GET /v1/_mw/quota-status` (Trạng thái Quota)
- [x] 3.6 Bổ sung section mới: `GET /v1/_mw/audit/query` (Truy vấn Audit Log)
- [x] 3.7 Bổ sung section mới: Notification endpoints (`/v1/_mw/admin/notifications`)
- [x] 3.8 Bổ sung section mới: Alert config endpoints (`/v1/_mw/admin/alerts/config`)
- [x] 3.9 Sửa mô tả Rate Limit — quota là cost USD, không phải request count
- [x] 3.10 Cập nhật ngày và phiên bản cuối tài liệu
