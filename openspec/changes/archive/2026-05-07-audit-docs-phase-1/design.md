## Context

Hệ thống tài liệu Markdown của dự án (trong thư mục `docs/`) đang đóng vai trò là Central Knowledge cho cả đội ngũ phát triển và quản trị vận hành. Do trải qua nhiều đợt nâng cấp (đổi sang PGVector, middleware chuyển sang port 5000, thay đổi chunk size của RAG, v.v.), có 5 file lõi liên quan đến kiến trúc và cơ sở dữ liệu bị lệch chuẩn định dạng (table thiếu cột STT, gãy hàng) hoặc thông tin bị cũ. Phase 1 sẽ quét và fix quy chuẩn cho nhóm 5 file này.

## Goals / Non-Goals

**Goals:**
- Truyền đạt được 100% độ chính xác cho tài liệu kiến trúc kỹ thuật.
- Chuẩn hoá format bảng biểu: Đảm bảo Markdown table render thẳng hàng.
- Thêm cột thứ tự đánh số liên tục (STT) vào tất cả các bảng.
- Sửa lại các chỉ số phần cứng/cấu hình sai sót (ví dụ: pgvector HNSW dim).

**Non-Goals:**
- Thay đổi cấu trúc luồng của mã nguồn.
- Kiểm toán các file tài liệu User Guide, Testing Form (Những file đó sẽ được xem xét ở các Phase sau).

## Decisions

- Sử dụng format `multi_replace_file_content` hoặc tiếp cận sửa tuần tự từng phần nhỏ trong Markdown nhằm đảm bảo tránh phá vỡ những link anchor `<div align="...">` cũ nếu có.
- STT sẽ được tự động đếm trên các dòng nội dung, loại trừ tiêu đề và dải phân cách bảng `|---|`. 

## Risks / Trade-offs

- [Nguy cơ vỡ Layout] → Mitigation: Sau khi fix một table, luôn sử dụng Markdown renderer (hoặc kiểm tra tính hợp lệ bằng mắt) để đảm bảo không bị thiếu dấu `|`.
