## Context

Ba tài liệu kỹ thuật (DOC-02, DOC-06, DOC-07) được viết vào tháng 3/2026 và chưa được đồng bộ với các thay đổi triển khai gần đây. Nguồn chân lý là: `docker-compose.yml`, `llm-mw/main.py`, `litellm/litellm_config.yaml`.

## Goals / Non-Goals

**Goals:**
- Đồng bộ nội dung 3 file tài liệu với hệ thống thực đang chạy
- Sửa các giá trị sai (routes, chunk sizes, vector dimensions)
- Bổ sung các endpoints API mới chưa được ghi nhận

**Non-Goals:**
- Không thay đổi source code
- Không thêm tính năng mới vào hệ thống
- Không cấu trúc lại bố cục tài liệu

## Decisions

**D1: Chỉ sửa nội dung sai, giữ nguyên cấu trúc**
Thay thế minimal — chỉ sửa các giá trị, route, diagram không chính xác. Không rewrite toàn bộ.

**D2: Verification source of truth**
- Routes: đọc từ `llm-mw/main.py` (app.add_api_route)
- Config values: đọc từ `docker-compose.yml` (environment section open-webui service)
- Module structure: đọc từ `llm-mw/` directory listing
- Model list: đọc từ `litellm/litellm_config.yaml`
- DB schema: đọc từ DOC-05 (được coi là đúng)
- Summary response: đọc từ `llm-mw/api/summary_v2.py` (return dict)

## Risks / Trade-offs

- [Risk] Một số trường trong summary response có thể thay đổi trong tương lai → **Mitigation**: ghi rõ "phiên bản 4.0-modular" và ngày cập nhật
- [Risk] Tài liệu DOC-07 đang là reference cho team dev → cần review kỹ trước khi finalize
