## ADDED Requirements

### Requirement: Tài liệu vận hành phản ánh đúng routes middleware
Tài liệu DOC-02 và DOC-07 SHALL sử dụng đúng URL path của các API endpoints theo định nghĩa trong `llm-mw/main.py`.

#### Scenario: Dashboard login route chính xác
- **WHEN** admin đọc tài liệu để gọi API đăng nhập dashboard
- **THEN** tài liệu MUST chỉ ra đúng route `POST /v1/_mw/dashboard/login`

#### Scenario: Route reconcile chính xác
- **WHEN** admin cần chạy reconcile thủ công theo tài liệu
- **THEN** tài liệu MUST chỉ ra đúng route `POST /admin/reconcile`

### Requirement: Tài liệu RAG phản ánh đúng giá trị config
Tài liệu DOC-06 SHALL sử dụng đúng giá trị chunk_size, chunk_overlap, và vector dimension theo docker-compose.yml.

#### Scenario: Chunk size và overlap chính xác
- **WHEN** developer đọc DOC-06 để hiểu cấu hình RAG
- **THEN** tài liệu MUST hiển thị chunk_size=1500, chunk_overlap=100 (không phải 1000/200)

#### Scenario: Vector dimension chính xác
- **WHEN** developer đọc retrieval pipeline diagram
- **THEN** tài liệu MUST hiển thị `vector(1536)` (không phải `vector(384)`)

### Requirement: Tài liệu API phản ánh đủ endpoints
Tài liệu DOC-07 SHALL liệt kê đủ các API endpoints hiện có trong middleware v4.0.

#### Scenario: Endpoints mới được ghi nhận
- **WHEN** developer tìm kiếm cách gọi embeddings, quota-status hoặc notifications
- **THEN** tài liệu MUST có section mô tả các endpoint sau: `/v1/embeddings`, `/v1/_mw/quota-status`, `/v1/_mw/audit/query`, `/v1/_mw/admin/notifications`, `/v1/_mw/admin/alerts/config`

#### Scenario: Summary response schema đầy đủ
- **WHEN** developer đọc schema phản hồi của `/v1/_mw/summary`
- **THEN** tài liệu MUST bao gồm các trường: `pending_open_count`, `embedding_calls`, `video_calls`, `billable_calls`
