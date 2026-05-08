# Proposal: Audit Docs Phase 2 — Giao tiếp API & Backend

## Mục tiêu

Chuẩn hoá và kiểm tra độ chính xác nhóm tài liệu liên quan đến giao tiếp API và backend infrastructure:
- `07-api-reference.md` — Tài liệu API Reference đầy đủ
- `15-nginx-https.md` — Nginx reverse proxy + SSL configuration
- `16-web-search.md` — Web Search (SearXNG) configuration
- `api-features-context-caching.md` — Context caching feature

## Phạm vi

1. Thêm cột STT vào tất cả Markdown Tables chưa có
2. Căn lề thẳng hàng toàn bộ bảng
3. Kiểm tra routes/endpoint paths khớp với `main.py` thực tế
4. Cập nhật model names trong ví dụ (thay tên cũ → tên thực tế trong production)
5. Cập nhật response schema `/v1/_mw/summary` đầy đủ các trường mới
6. Rà soát cấu hình Nginx, SearXNG, context caching đảm bảo phản ánh đúng production

## Ghi chú

`02-tai-lieu-van-hanh.md`, `08-dashboard.md`, `09-user-management.md` thuộc Phase 3 (Vận hành & Quản trị).
