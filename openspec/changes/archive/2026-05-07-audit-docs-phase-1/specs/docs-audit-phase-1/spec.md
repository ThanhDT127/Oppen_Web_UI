## ADDED Requirements

### Requirement: Dữ liệu cấu trúc bảng chuẩn Markdown
Các file tài liệu (01, 03, 04, 05, 06) SHALL định dạng đúng tất cả các loại markdown table.

#### Scenario: Bảng bị thiếu cột STT
- **WHEN** phát hiện một bảng danh sách (danh sách host, port, API, logic...)
- **THEN** bảng MUST được cập nhật để có thêm phần cột STT trước tiên và đánh số tăng dần liên tục.

### Requirement: Nội dung cấu hình chính xác
Tất cả các thông số được nhắc đến trong 5 file đầu tiên SHALL sử dụng giá trị hiện tại của hệ thống.

#### Scenario: Vector Settings
- **WHEN** file nhắc đến Embedding Vector
- **THEN** tài liệu MUST ghi nhận số chiều của Model là 1536 chứ không phải 384.

#### Scenario: RAG Chunking
- **WHEN** nhắc tới Chunking Logic
- **THEN** kích thước chunk size MUST phản ánh giá trị 1500 (và chunk overlap là 100).
