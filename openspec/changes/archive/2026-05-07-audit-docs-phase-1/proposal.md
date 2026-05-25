## Why

Hệ thống tài liệu (.md) đóng vai trò là "nguồn chân lý" (source of truth) cho hệ thống Open WebUI Middleware. Hiện tại, các file tài liệu có nhiều chỗ định dạng bảng biểu chưa chuẩn (thiếu cột STT, lệch cột) và thông tin có thể quá hạn so với mã nguồn thực tế. Cần có đợt kiểm toán tổng thể để độ chính xác của tài liệu đạt mức tối đa. Phase 1 sẽ tập trung rà soát nhóm tài liệu lõi: Tổng quan, Kiến trúc và Cơ sở dữ liệu.

## What Changes

- Quét và quy chuẩn hoá 5 file tài liệu: `01-tong-quan-he-thong.md`, `03-architecture.md`, `04-architecture-diagrams.md`, `05-database-architecture.md`, `06-rag-architecture.md`.
- Sửa lại các bảng (table): tự động thêm cột STT, format thẳng hàng, đổi tên cột cho chính xác.
- Kiểm tra tính chính xác của dữ liệu, nội dung và biểu đồ theo logic hiện tại.

## Capabilities

### New Capabilities
- `docs-audit-phase-1`: Đưa ra tiêu chuẩn rà soát (audit) bảng biểu, nội dung, schema để dùng làm thước đo cho tài liệu kiến trúc lõi của hệ thống.

### Modified Capabilities
- (Không có file spec cũ nào bị thay đổi do đây là spec mới phục vụ riêng cho đợt kiểm toán)

## Impact

- Cải thiện đáng kể chất lượng tài liệu lõi, làm cơ sở xây dựng các Phase sau.
- Toàn bộ nội dung tài liệu sẽ phản ánh 100% độ chính xác của code hiện tại (middleware endpoints, vecto DB schema, v.v.).
