# CHECK LIST TÍNH NĂNG OPEN WEBUI

> **Ngày cập nhật**: 2026-03-03  
> **Phiên bản hệ thống**: Open WebUI + LiteLLM + Middleware + PostgreSQL/PGVector

---

## Cấu trúc bảng

| Cột | Mô tả |
|-----|-------|
| STT | Số thứ tự |
| Module | Nhóm chức năng lớn |
| Nhóm tính năng | Phân nhóm con |
| Tính năng cụ thể | Mô tả tính năng |
| Hướng dẫn sử dụng / Mô tả | Cách sử dụng hoặc đầu vào/đầu ra |
| Câu lệnh ví dụ | Ví dụ thực tế |
| Trạng thái | Đã có / Chưa có / Đang phát triển |
| Kết quả test | OK / Đang lỗi / Chưa test |
| Ghi chú | Thông tin bổ sung |

---

## I. PHÂN QUYỀN & QUẢN LÝ NGƯỜI DÙNG

| STT | Nhóm tính năng | Tính năng cụ thể | Hướng dẫn sử dụng / Mô tả | Câu lệnh ví dụ | Trạng thái | Kết quả test | Ghi chú |
|-----|----------------|-------------------|----------------------------|----------------|-----------|-------------|---------|
| 1 | Đăng ký & Đăng nhập | Đăng ký tài khoản bằng email/password | Người dùng truy cập `http://<server>:3000`, chọn "Sign Up", điền tên, email, mật khẩu | — | Đã có | OK | `ENABLE_SIGNUP=true` |
| 2 | | Đăng nhập bằng email/password | Nhập email + password → nhận JWT token | — | Đã có | OK | |
| 3 | | Hỗ trợ OAuth/SSO | Cho phép đăng nhập qua AD/LDAP/Google/Microsoft | — | Hạ tầng có | Chưa test | Cần cấu hình `OAUTH_*` env |
| 4 | Phân quyền | 3 cấp bậc: Admin, User, Pending | **Admin**: quản lý toàn bộ (users, models, knowledge, settings). **User**: sử dụng chat, upload file, tạo knowledge cá nhân. **Pending**: chờ admin duyệt | — | Đã có | OK | |
| 5 | | Quản lý user (Admin) | Admin có thể: thêm/xoá user, đổi role, reset password, xem danh sách user | Admin → Settings → Users | Đã có | OK | |
| 6 | | Access Control trên Knowledge | Mỗi Knowledge Collection có thể giới hạn quyền truy cập theo user/group | Cấu hình trong Knowledge Settings | Đã có | OK | Hỗ trợ JSON access_control |
| 7 | | Access Control trên Model | Admin có thể giới hạn model nào user nào được dùng | Admin → Settings → Models | Đã có | OK | |
| 8 | Quản lý log (Admin) | Log hoạt động API requests | Middleware ghi log mọi request: user, model, tokens, cost, timestamp | Dashboard → Logs tab hoặc Access tab | Đã có | OK | Lưu trong PostgreSQL (mw_audit_log, mw_request_log) + file backup |
| 9 | | Dashboard quản trị | Xem tổng quan chi phí, số request, top users, top models | `http://<server>:5000/dashboard` | Đã có | OK | Middleware dashboard |

---

## II. CHAT AI ĐA MÔ HÌNH

| STT | Nhóm tính năng | Tính năng cụ thể | Hướng dẫn sử dụng / Mô tả | Câu lệnh ví dụ | Trạng thái | Kết quả test | Ghi chú |
|-----|----------------|-------------------|----------------------------|----------------|-----------|-------------|---------|
| 1 | OpenAI GPT-5 | Chat GPT-5 (Flagship) | Model mạnh nhất, đa phương thức (text + hình) | "Phân tích hình ảnh này và cho nhận xét" | Đã có | OK | `chat-gpt-5` |
| 2 | | Chat GPT-5 Mini | Nhanh hơn GPT-5, phù hợp tác vụ thông thường | "Tóm tắt email này" | Đã có | OK | `chat-gpt-5-mini` |
| 3 | | Chat GPT-5 Nano | Nhẹ nhất, chi phí thấp | "Dịch câu này sang tiếng Anh" | Đã có | OK | `chat-gpt-5-nano` |
| 4 | OpenAI GPT-4o | Chat GPT-4o | Multimodal nhanh, hỗ trợ hình ảnh | "Mô tả nội dung hình ảnh" | Đã có | OK | `chat-gpt-4o` |
| 5 | | Chat GPT-4o Mini | Nhanh, rẻ, đủ tốt cho hầu hết tác vụ | "Viết email trả lời khách hàng" | Đã có | OK | `chat-gpt-4o-mini` |
| 6 | OpenAI GPT-4.1 | Chat GPT-4.1 | Context window 1 triệu token, xử lý tài liệu dài | "Phân tích toàn bộ báo cáo 200 trang này" | Đã có | OK | `chat-gpt-4.1` |
| 7 | | Chat GPT-4.1 Mini | 1M context, chi phí thấp hơn | "Tóm tắt tài liệu dài" | Đã có | OK | `chat-gpt-4.1-mini` |
| 8 | | Chat GPT-4.1 Nano | 1M context, chi phí thấp nhất | "Trích xuất thông tin từ file lớn" | Đã có | OK | `chat-gpt-4.1-nano` |
| 9 | Google Gemini 2.5 | Chat Gemini 2.5 Pro | Reasoning mạnh, hỗ trợ tiếng Việt tốt | "Giải thích khái niệm quantum computing" | Đã có | OK | `chat-gemini-2.5-pro` |
| 10 | | Chat Gemini 2.5 Flash | Nhanh, cân bằng giữa tốc độ và chất lượng | "Viết code Python sort danh sách" | Đã có | OK | `chat-gemini-2.5-flash` |
| 11 | | Chat Gemini 2.5 Flash Lite | Nhẹ nhất Gemini, rẻ | "Kiểm tra ngữ pháp câu này" | Đã có | OK | `chat-gemini-2.5-flash-lite` |
| 12 | Google Gemini 2.0 | Chat Gemini 2.0 Flash | Thế hệ trước, vẫn ổn định | "Chat thông thường" | Đã có | OK | `chat-gemini-2.0-flash` |
| 13 | | Chat Gemini 2.0 Flash Lite | Nhẹ, nhanh | "Trả lời câu hỏi đơn giản" | Đã có | OK | `chat-gemini-2.0-flash-lite` |
| 14 | Google Gemini 3 | Chat Gemini 3 Pro | Flagship mới nhất của Google | "Phân tích dữ liệu phức tạp" | Đã có | OK | `chat-gemini-3-pro` |
| 15 | Tính năng chat | Streaming response | Response hiển thị từng token realtime | — | Đã có | OK | |
| 16 | | Chat history | Lưu lại toàn bộ lịch sử hội thoại | — | Đã có | OK | Lưu trong PostgreSQL |
| 17 | | Pin / Archive chat | Ghim hoặc lưu trữ hội thoại quan trọng | — | Đã có | OK | |
| 18 | | Share chat | Chia sẻ hội thoại qua link công khai | — | Đã có | OK | |
| 19 | | Folder tổ chức chat | Sắp xếp hội thoại vào folder | — | Đã có | OK | |
| 20 | | Tags | Gắn tag cho hội thoại để phân loại | — | Đã có | OK | |
| 21 | | Chuyển model giữa chừng | Đổi model trong cùng 1 hội thoại | Chọn model khác từ dropdown | Đã có | OK | |
| 22 | | Multimodal input | Gửi hình ảnh kèm text trong chat | Kéo thả/paste hình vào chat | Đã có | OK | Với GPT-4o, Gemini |

---

## III. TẠO ẢNH AI (IMAGE GENERATION)

| STT | Nhóm tính năng | Tính năng cụ thể | Hướng dẫn sử dụng / Mô tả | Câu lệnh ví dụ | Trạng thái | Kết quả test | Ghi chú |
|-----|----------------|-------------------|----------------------------|----------------|-----------|-------------|---------|
| 1 | DALL-E 3 | Tạo ảnh từ text (OpenAI) | Chọn model `img-gpt-dalle-3`, nhập mô tả → nhận ảnh | "Vẽ hình con mèo đang đọc sách" | Đã có | OK | 1024x1024 |
| 2 | Gemini Image | Tạo ảnh nhanh (Gemini Flash) | Chọn `img-gemini-flash`, nhập mô tả → nhận ảnh | "Tạo logo công ty màu xanh" | Đã có | OK | 1024px |
| 3 | | Tạo ảnh chất lượng cao (Gemini Pro) | Chọn `img-gemini-pro`, nhập mô tả | "Thiết kế poster quảng cáo sản phẩm đèn LED" | Đã có | OK | Lên đến 4K |

---

## IV. GIỌNG NÓI (VOICE)

| STT | Nhóm tính năng | Tính năng cụ thể | Hướng dẫn sử dụng / Mô tả | Câu lệnh ví dụ | Trạng thái | Kết quả test | Ghi chú |
|-----|----------------|-------------------|----------------------------|----------------|-----------|-------------|---------|
| 1 | Text-to-Speech | Chuyển text thành giọng nói | AI đọc nội dung response bằng giọng nói tự nhiên | Nhấn icon 🔊 trên response | Đã có | OK | `tts-gpt-4o-mini` |
| 2 | Speech-to-Text | Nhập liệu bằng giọng nói | Nói vào mic → AI chuyển thành text → gửi prompt | Nhấn icon 🎤 trong chat | Đã có | OK | `stt-gpt-4o` |
| 3 | | Phiên bản nhẹ STT | Nhận dạng giọng nói nhanh hơn, chi phí thấp | — | Đã có | OK | `stt-gpt-4o-mini` |

---

## V. RAG – KNOWLEDGE BASE (CƠ SỞ TRI THỨC)

| STT | Nhóm tính năng | Tính năng cụ thể | Hướng dẫn sử dụng / Mô tả | Câu lệnh ví dụ | Trạng thái | Kết quả test | Ghi chú |
|-----|----------------|-------------------|----------------------------|----------------|-----------|-------------|---------|
| 1 | Quản lý Knowledge | Tạo Knowledge Collection | Workspace → Knowledge → Create. Đặt tên, mô tả | — | Đã có | OK | |
| 2 | | Upload file vào Knowledge | Upload PDF, DOCX, TXT, CSV, MD, HTML, Excel | Kéo thả file vào Knowledge | Đã có | OK | Max 50MB/file |
| 3 | | Xoá file khỏi Knowledge | Xoá file → xoá luôn vector embeddings tương ứng | — | Đã có | OK | CASCADE delete |
| 4 | | Access control Knowledge | Giới hạn ai được truy cập Knowledge nào | Cấu hình trong Knowledge settings | Đã có | OK | |
| 5 | Sử dụng trong chat | Gọi Knowledge bằng `#` | Trong chat, gõ `#tên-knowledge` để chọn | `#tai-lieu-noi-bo Chính sách nghỉ phép?` | Đã có | OK | |
| 6 | | Attach file trực tiếp | Kéo thả file vào chat, AI đọc và trả lời | Kéo file PDF vào chat box | Đã có | OK | Xử lý tạm thời, không lưu lâu dài |
| 7 | | Gán Knowledge vào Model | Admin gán Knowledge mặc định cho model cụ thể | Admin → Models → Knowledge | Đã có | OK | |
| 8 | Tìm kiếm | Hybrid Search (BM25 + Vector) | Kết hợp keyword matching + semantic search | — | Đã có | OK | `ENABLE_RAG_HYBRID_SEARCH=true` |
| 9 | | HNSW Vector Index | Tìm kiếm approximate nearest neighbor nhanh | — | Đã có | OK | m=16, ef_construction=64 |
| 10 | | Citation (trích dẫn nguồn) | AI trích dẫn tên file và trang nguồn trong câu trả lời | — | Đã có | OK | |
| 11 | Embedding | Multilingual embedding (local) | Model chạy local, hỗ trợ 50+ ngôn ngữ | — | Đã có | OK | `paraphrase-multilingual-MiniLM-L12-v2` |
| 12 | | Không gửi dữ liệu ra ngoài | Embedding chạy trên server, dữ liệu không rời khỏi hệ thống | — | Đã có | OK | Bảo mật dữ liệu nội bộ |
| 13 | Cấu hình | Chunk size | 1000 ký tự / chunk | — | Đã có | OK | Có thể điều chỉnh |
| 14 | | Chunk overlap | 200 ký tự overlap giữa các chunks | — | Đã có | OK | Giữ context liên tục |
| 15 | Định dạng file | PDF | Extract text từ PDF (có hỗ trợ OCR) | — | Đã có | OK | |
| 16 | | Word (.docx) | Extract text từ file Word | — | Đã có | OK | |
| 17 | | Excel (.xlsx) | Extract text từ file Excel | — | Đã có | OK | |
| 18 | | Text (.txt, .csv, .md) | Đọc trực tiếp | — | Đã có | OK | |
| 19 | | HTML | Extract text từ trang web | — | Đã có | OK | |

---

## VI. CÔNG CỤ MỞ RỘNG (CUSTOM TOOLS)

| STT | Nhóm tính năng | Tính năng cụ thể | Hướng dẫn sử dụng / Mô tả | Câu lệnh ví dụ | Trạng thái | Kết quả test | Ghi chú |
|-----|----------------|-------------------|----------------------------|----------------|-----------|-------------|---------|
| 1 | Xuất Excel | Trích xuất dữ liệu hội thoại → Excel | Nhấn icon Action → "Xuất Excel". Hệ thống chuẩn hoá nội dung thành bảng Markdown rồi tạo file .xlsx có định dạng, filter, freeze header | Chat nội dung bảng biểu → nhấn icon xuất | Đã có | OK | `tool excel.py` |
| 2 | | Wizard UI khi xuất | Hiển thị modal progress: 3 bước (chuẩn hoá → tạo file → tải xuống) | — | Đã có | OK | UX thân thiện |
| 3 | | Auto-detect số, ngày, % | Tự nhận dạng kiểu dữ liệu trong bảng: số có dấu phẩy, ngày tháng, phần trăm | — | Đã có | OK | |
| 4 | | Hỗ trợ tiền tệ VNĐ, $, € | Nhận dạng và format đúng tiền tệ | — | Đã có | OK | |
| 5 | Xuất PDF | Xuất nội dung hội thoại → PDF | Nhấn icon Action → "Xuất PDF" | — | Đã có | OK | `tool pdf.py` |
| 6 | Xuất DOCX | Xuất nội dung hội thoại → Word | Nhấn icon Action → "Xuất DOCX" | — | Đã có | OK | `tool docx.py` |
| 7 | Custom Functions | Framework tạo function tuỳ chỉnh | Admin có thể thêm Python functions chạy trong Open WebUI | — | Đã có | Chưa test | Hạ tầng sẵn sàng |
| 8 | Custom Tools | Framework tạo tool tuỳ chỉnh | Admin có thể tạo tools cho AI gọi (function calling) | — | Đã có | Chưa test | Hạ tầng sẵn sàng |

---

## VII. KIỂM SOÁT CHI PHÍ & QUOTA (MIDDLEWARE)

| STT | Nhóm tính năng | Tính năng cụ thể | Hướng dẫn sử dụng / Mô tả | Câu lệnh ví dụ | Trạng thái | Kết quả test | Ghi chú |
|-----|----------------|-------------------|----------------------------|----------------|-----------|-------------|---------|
| 1 | Quota | Giới hạn chi phí / user / tháng | Cấu hình qua Dashboard hoặc API: mỗi user có `limit_cost_usd` | — | Đã có | OK | Lưu trong PostgreSQL (mw_users) |
| 2 | | Cảnh báo khi gần hết quota | User nhận thông báo khi sử dụng gần hết quota | — | Đã có | OK | |
| 3 | | Chặn khi hết quota | Từ chối request khi user vượt quota | — | Đã có | OK | HTTP 429 |
| 4 | Sub-keys | Cấp API key riêng | Mỗi user/nhóm có sub-key riêng biệt | — | Đã có | OK | Trong DB (mw_users), backup `users.json` |
| 5 | Cost tracking | Ghi log chi phí từng request | Log: model, input_tokens, output_tokens, cost_usd, user, timestamp | — | Đã có | OK | DB (mw_audit_log) + file backup |
| 6 | | Tính chi phí theo bảng giá | Bảng giá riêng cho từng model, lưu trong DB (backup: `prices.json`) | — | Đã có | OK | |
| 7 | Dashboard | Xem báo cáo chi phí | Dashboard web hiển thị: tổng chi phí, theo user, theo model, theo ngày | `http://<server>:5000/dashboard` | Đã có | OK | |

---

## VIII. DATABASE & HẠ TẦNG

| STT | Nhóm tính năng | Tính năng cụ thể | Hướng dẫn sử dụng / Mô tả | Câu lệnh ví dụ | Trạng thái | Kết quả test | Ghi chú |
|-----|----------------|-------------------|----------------------------|----------------|-----------|-------------|---------|
| 1 | PostgreSQL | Database chính | PostgreSQL 16, lưu toàn bộ data (users, chats, knowledge, vectors) | — | Đã có | OK | 32 tables (openwebui) + 6 tables (middleware) |
| 2 | | PGVector extension | Vector similarity search cho RAG, HNSW index | — | Đã có | OK | v0.8.0 |
| 3 | | Persistent storage | Docker volume `postgres_data` giữ data khi restart | — | Đã có | OK | |
| 4 | Docker | 4 containers orchestra | PostgreSQL + LiteLLM + Middleware + Open WebUI | `docker compose up -d` | Đã có | OK | |
| 5 | | Health checks | Tự kiểm tra sức khoẻ và restart nếu container lỗi | — | Đã có | OK | `restart: unless-stopped` |
| 6 | | Auto-restart | Container tự restart khi server reboot | — | Đã có | OK | |
| 7 | Backup | Manual backup | `pg_dump` full database | `docker exec openwebui-postgres pg_dump ...` | Đã có | Chưa test | Cần chạy thủ công |
| 8 | Network | Internal Docker network | Các container giao tiếp qua mạng Docker riêng, không expose port nội bộ | — | Đã có | OK | `openwebui-network` |
| 9 | Firewall | Port 3000 (WebUI) | Đã mở firewall cho truy cập từ bên ngoài | — | Đã có | OK | |
| 10 | | Port 5000 (API/Middleware) | Đã mở firewall cho truy cập API | — | Đã có | OK | |

---

## IX. TÍNH NĂNG DÀNH CHO NGƯỜI DÙNG (END-USER)

| STT | Nhóm tính năng | Tính năng cụ thể | Hướng dẫn sử dụng / Mô tả | Câu lệnh ví dụ | Trạng thái | Kết quả test | Ghi chú |
|-----|----------------|-------------------|----------------------------|----------------|-----------|-------------|---------|
| 1 | Giao diện | Giao diện web responsive | Truy cập qua trình duyệt, hỗ trợ desktop và mobile | — | Đã có | OK | |
| 2 | | Dark mode / Light mode | Chuyển đổi giao diện sáng/tối | Settings → Theme | Đã có | OK | |
| 3 | | Đa ngôn ngữ | Giao diện hỗ trợ nhiều ngôn ngữ (tiếng Việt, tiếng Anh, ...) | Settings → Language | Đã có | OK | |
| 4 | Cá nhân hoá | Chọn model mặc định | User chọn model ưa thích làm mặc định | Settings → Default Model | Đã có | OK | |
| 5 | | System prompt cá nhân | User tự đặt system prompt riêng | Settings → System Prompt | Đã có | OK | |
| 6 | | Memory (AI nhớ user) | AI lưu thông tin user để cá nhân hoá câu trả lời | "Nhớ rằng tôi là developer Python" | Đã có | OK | Lưu trong table `memory` |
| 7 | Tìm kiếm | Tìm kiếm trong lịch sử chat | Tìm theo keyword trong tiêu đề hoặc nội dung chat | Thanh search trên sidebar | Đã có | OK | |
| 8 | Chia sẻ | Chia sẻ hội thoại | Tạo link chia sẻ hội thoại cho người khác xem | Share icon → Copy link | Đã có | OK | |
| 9 | Xuất dữ liệu | Export chat history | Xuất lịch sử chat thành file | — | Đã có | OK | |
| 10 | | Xuất Excel/PDF/DOCX | Sử dụng custom tools để xuất dữ liệu có format | Action → Xuất Excel / PDF / DOCX | Đã có | OK | |
| 11 | Prompt | Saved Prompts | Lưu prompt hay dùng để tái sử dụng | Workspace → Prompts | Đã có | Chưa test | Hạ tầng sẵn |
| 12 | | Prompt suggestions | Gợi ý câu hỏi khi mở chat mới | — | Đã có | OK | Cấu hình qua Admin |

---

## X. TÍNH NĂNG DÀNH CHO ADMIN

| STT | Nhóm tính năng | Tính năng cụ thể | Hướng dẫn sử dụng / Mô tả | Câu lệnh ví dụ | Trạng thái | Kết quả test | Ghi chú |
|-----|----------------|-------------------|----------------------------|----------------|-----------|-------------|---------|
| 1 | Quản lý User | Danh sách user | Xem tất cả users, role, trạng thái | Admin Panel → Users | Đã có | OK | |
| 2 | | Duyệt user mới | Approve/Reject user pending | — | Đã có | OK | |
| 3 | | Đổi role user | Thăng/hạ quyền (Admin ↔ User) | — | Đã có | OK | |
| 4 | | Xoá user | Xoá tài khoản user | — | Đã có | OK | |
| 5 | Quản lý Model | Bật/tắt model | Enable/disable model cho users | Admin → Models | Đã có | OK | |
| 6 | | Cấu hình model params | Set temperature, top_p, max_tokens mặc định | — | Đã có | OK | |
| 7 | | Gán Knowledge vào model | Model tự động dùng Knowledge cụ thể | — | Đã có | OK | |
| 8 | Quản lý Knowledge | Xem tất cả Knowledge | Liệt kê toàn bộ Knowledge Collections | Admin → Knowledge | Đã có | OK | |
| 9 | | Xoá Knowledge | Xoá collection + toàn bộ embeddings | — | Đã có | OK | CASCADE delete |
| 10 | Cấu hình RAG | Điều chỉnh chunk size | Thay đổi kích thước chunk khi embed | ENV: `CHUNK_SIZE=1000` | Đã có | OK | |
| 11 | | Điều chỉnh file size limit | Giới hạn dung lượng file upload | ENV: `RAG_FILE_MAX_SIZE=50` | Đã có | OK | Hiện 50 MB |
| 12 | | Đổi embedding model | Chuyển đổi giữa local / OpenAI embeddings | ENV: `RAG_EMBEDDING_MODEL=...` | Đã có | OK | |
| 13 | Cấu hình hệ thống | WebUI settings | Cấu hình: signup, default model, banner, v.v. | Admin → Settings → General | Đã có | OK | |
| 14 | | Connections | Cấu hình kết nối đến LLM providers | Admin → Settings → Connections | Đã có | OK | |
| 15 | Giám sát | Request logs | Xem log chi tiết từng API request | Dashboard → Logs tab (DB: mw_audit_log) | Đã có | OK | |
| 16 | | Application logs | Xem lỗi, warning, events | `logs/middleware.log` | Đã có | OK | |
| 17 | | Cost dashboard | Báo cáo chi phí theo user/model/thời gian | `http://<server>:5000/dashboard` | Đã có | OK | |

---

## XI. TÍNH NĂNG CHƯA TRIỂN KHAI (KẾ HOẠCH)

| STT | Nhóm tính năng | Tính năng cụ thể | Hướng dẫn sử dụng / Mô tả | Trạng thái | Ghi chú |
|-----|----------------|-------------------|----------------------------|-----------|---------|
| 1 | Nhóm người dùng | Tạo nhóm theo phòng ban | Phân quyền và quota theo nhóm | Chưa có | Framework có sẵn (table `group`) |
| 2 | Backup tự động | Scheduled backup database | Cron job chạy pg_dump hàng ngày | Chưa có | Cần cài đặt |
| 3 | Monitoring | Uptime monitoring + alerting | Prometheus + Grafana hoặc tương đương | Chưa có | |
| 4 | SSO/LDAP | Đăng nhập bằng AD nội bộ | Tích hợp Active Directory | Chưa có | Open WebUI hỗ trợ sẵn |
| 5 | Mobile app | Ứng dụng mobile native | iOS/Android app | Chưa có | Web responsive đã hỗ trợ |
| 6 | API integration | Tích hợp DMS, ERP | Kết nối với hệ thống nội bộ khác | Chưa có | Middleware API sẵn sàng |
| 7 | Scheduled reports | Báo cáo chi phí tự động | Email/Zalo báo cáo chi phí hàng tuần | Chưa có | |
| 8 | Fine-tuning | Huấn luyện model riêng | Train model trên dữ liệu nội bộ | Chưa có | Cần GPU |
| 9 | On-premise LLM | Chạy AI local (Llama, Mistral) | Không phụ thuộc API bên ngoài | Chưa có | Cần GPU mạnh |
| 10 | Web crawling | Crawl dữ liệu từ web | Tự động fetch và index dữ liệu web | Chưa có | Open WebUI hỗ trợ sẵn URL import |

---

## Tổng kết

| Nhóm | Số tính năng đã có | Chưa có / Kế hoạch |
|------|-------------------|-------------------|
| I. Phân quyền & Quản lý | 9 | 1 (Groups) |
| II. Chat AI | 22 | — |
| III. Tạo ảnh AI | 3 | — |
| IV. Giọng nói | 3 | — |
| V. RAG / Knowledge | 19 | — |
| VI. Custom Tools | 8 | — |
| VII. Chi phí & Quota | 7 | — |
| VIII. Database & Hạ tầng | 10 | 1 (Auto backup) |
| IX. Tính năng End-user | 12 | — |
| X. Tính năng Admin | 17 | — |
| XI. Kế hoạch tương lai | — | 10 |
| **Tổng** | **110** | **12** |

> **110 tính năng đã hoạt động** / 12 tính năng trong kế hoạch phát triển.
