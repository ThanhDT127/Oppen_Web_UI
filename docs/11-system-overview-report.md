# BÁO CÁO TỔNG QUAN HỆ THỐNG AI NỘI BỘ (OPEN WEBUI)

> **Đơn vị thực hiện**: Đội kỹ thuật AI  
> **Ngày lập**: 2026-02-10  
> **Phiên bản**: 2.0  
> **Đối tượng**: Ban lãnh đạo, Quản trị viên, Trưởng bộ phận

---

## 1. TÓM TẮT DÀNH CHO LÃNH ĐẠO

### Hệ thống là gì?

Hệ thống AI nội bộ (Open WebUI) là **nền tảng trợ lý AI tập trung** cho toàn tổ chức, hoạt động như một "ChatGPT nội bộ" nhưng có **kiểm soát chi phí**, **bảo mật dữ liệu**, và **quản trị tập trung**.

Thay vì mỗi nhân viên đăng ký tài khoản ChatGPT riêng lẻ (rủi ro rò rỉ dữ liệu, không kiểm soát chi phí), hệ thống cung cấp **một cổng truy cập duy nhất** cho tất cả dịch vụ AI.

### Giá trị kinh doanh

| #   | Giá trị                    | Mô tả chi tiết                                                                                         |
| --- | -------------------------- | ------------------------------------------------------------------------------------------------------ |
| 1   | **Tiết kiệm chi phí**      | Một tài khoản API, kiểm soát quota từng người, tránh chi phí phát sinh ngoài kế hoạch                  |
| 2   | **Bảo mật dữ liệu nội bộ** | Tài liệu nội bộ lưu trên server riêng, vectors lưu on-premise trong PGVector. Embedding qua Gemini API (text chunks gửi qua Google để chuyển thành vectors) |
| 3   | **Năng suất nhân viên**    | Hỗ trợ soạn thảo, phân tích, báo cáo, dịch thuật, tra cứu – tiết kiệm 30-50% thời gian thao tác lặp    |
| 4   | **Tri thức tập trung**     | Upload tài liệu nội bộ → AI trả lời dựa trên chính sách, quy trình thực tế của công ty                 |
| 5   | **Đa phương thức**         | Không chỉ chat text – còn tạo ảnh, nhận dạng giọng nói, đọc tài liệu, xuất Excel/PDF                   |
| 6   | **Quản trị minh bạch**     | Theo dõi ai dùng gì, tốn bao nhiêu, thống kê chi phí theo thời gian                                    |

### Số liệu nổi bật

| Chỉ số                            | Giá trị                                                   |
| --------------------------------- | --------------------------------------------------------- |
| Tổng số mô hình AI sẵn sàng       | **19** (12 chat + 6 ảnh + 1 embedding)                    |
| Nhà cung cấp AI                   | **4** – OpenAI, Google Gemini, xAI Grok, Anthropic Claude |
| Tổng tính năng đã hoạt động       | **116**                                                   |
| Tính năng trong kế hoạch          | **12**                                                    |
| Dung lượng file upload RAG tối đa | **2048 MB / file**                                        |
| Ngôn ngữ hỗ trợ (AI + RAG)        | **50+ ngôn ngữ** (bao gồm tiếng Việt)                     |
| Thời gian triển khai              | **Docker Compose – khởi động trong 2 phút**               |

---

## 2. TÌNH TRẠNG HIỆN TẠI CỦA HỆ THỐNG

### 2.1. Trạng thái vận hành

| Thành phần                            | Trạng thái      | Ghi chú                                 |
| ------------------------------------  | --------------- | --------------------------------------- |
| 🟢 Giao diện web (Open WebUI)        | **Hoạt động**   | Truy cập qua HTTPS (Nginx :3000)          |
| 🟢 Middleware (Auth + Quota)         | **Hoạt động**   | Kiểm soát chi phí, phân quyền             |
| 🟢 LiteLLM (LLM Proxy)               | **Hoạt động**   | Kết nối OpenAI + Gemini + xAI + Anthropic |
| 🟢 PostgreSQL + PGVector             | **Hoạt động**   | Database + vector search                  |
| 🟢 Docling (OCR/Extract)             | **Hoạt động**   | Extract text từ PDF, DOCX                 |
| 🟢 Embedding qua Gemini API          | **Hoạt động**   | gemini-embedding-001, 1536-dim            |
| 🟢 Firewall mở port 3000             | **Đã cấu hình** | Truy cập qua Nginx HTTPS                  |

### 2.2. Người dùng

| Phân loại   | Mô tả                                                                    |
| ----------- | ------------------------------------------------------------------------ |
| **Admin**   | Toàn quyền quản trị: users, models, knowledge, settings, xem log chi phí |
| **User**    | Sử dụng chat AI, upload tài liệu, tạo knowledge cá nhân, xuất file       |
| **Pending** | Tài khoản đã đăng ký, chờ Admin duyệt mới được sử dụng                   |

> 💡 **Cách thêm người dùng**: Người dùng tự đăng ký tại trang web → Admin vào quản trị duyệt tài khoản → Người dùng bắt đầu sử dụng.

---

## 3. TÍNH NĂNG HỆ THỐNG – TỔNG QUAN

### 3.1. Chat AI thông minh (12 mô hình)

Hệ thống tích hợp **12 mô hình chat** từ 4 nhà cung cấp hàng đầu thế giới:

**OpenAI (3 models)**:
- **GPT-5.4**: Flagship mới nhất – reasoning, phân tích phức tạp, multimodal
- **GPT-5.2**: Cân bằng chất lượng và tốc độ
- **GPT-5**: Tiêu chuẩn, chi phí hợp lý

**Google Gemini (3 models)**:
- **Gemini 3.1 Pro Preview**: Flagship mới nhất của Google, reasoning mạnh
- **Gemini 3.1 Flash-Lite Preview**: Nhanh, chi phí thấp
- **Gemini 2.5 Flash**: Cân bằng tốc độ và chất lượng, tiếng Việt tốt

**xAI Grok (3 models)**:
- **Grok 4.20 Reasoning**: Reasoning mạnh, real-time data
- **Grok 4.1 Fast Reasoning**: Nhanh, reasoning
- **Grok 4.1 Fast Non-Reasoning**: Nhanh nhất, chi phí thấp

**Anthropic Claude (3 models)**:
- **Claude Opus 4.6**: Flagship, phân tích phức tạp
- **Claude Sonnet 4.6**: Cân bằng chất lượng và tốc độ
- **Claude Haiku 4.5**: Nhanh, chi phí thấp

**Ví dụ ứng dụng thực tế**:
- Soạn email phản hồi khách hàng trong 30 giây
- Tóm tắt báo cáo 100 trang thành 1 trang
- Phân tích dữ liệu bán hàng, đề xuất chiến lược
- Dịch tài liệu kỹ thuật tiếng Anh – Việt
- Viết script tự động hóa, hỗ trợ nghiệp vụ IT

### 3.2. Tạo ảnh AI (6 mô hình)

| Model                          | Nhà cung cấp | Mô tả                             |
| ------------------------------ | ------------ | --------------------------------- |
| **GPT-Image-1.5** (OpenAI)     | OpenAI       | Mới nhất, 4x nhanh hơn, 3 chất lượng |
| **GPT-Image-1** (OpenAI)       | OpenAI       | Chất lượng cao, 3 cấp độ          |
| **Gemini 3.1 Flash Image**     | Google       | Tạo ảnh nhanh, chi phí thấp       |
| **Gemini 3 Pro Image**         | Google       | Chất lượng cao                    |
| **Grok Imagine**               | xAI          | Tiêu chuẩn, $0.05/ảnh             |
| **Grok Imagine Pro**           | xAI          | Chất lượng cao, $0.10/ảnh          |

### 3.3. Giọng nói

| Tính năng          | Mô tả                  | Ứng dụng                                  |
| ------------------ | ---------------------- | ----------------------------------------- |
| **Text-to-Speech** | AI đọc lại câu trả lời | Nghe báo cáo khi di chuyển                |
| **Speech-to-Text** | Nói thay vì gõ         | Nhập liệu nhanh, người không quen gõ phím |

### 3.4. Cơ sở tri thức nội bộ (RAG – Knowledge Base) ⭐

Đây là tính năng **giá trị nhất** cho doanh nghiệp: upload tài liệu nội bộ → AI trả lời dựa trên **chính tài liệu của công ty**.

**Cách hoạt động**:
1. Admin/User upload tài liệu (PDF, Word, Excel, v.v.) vào "Knowledge" 
2. Hệ thống tự động đọc, chia nhỏ, chuyển thành dữ liệu tìm kiếm
3. Khi user hỏi, AI tìm đoạn liên quan trong tài liệu → trả lời kèm trích dẫn nguồn

**Ví dụ thực tế**:
- Upload "Quy chế nhân sự.pdf" → hỏi "Chính sách nghỉ phép?" → AI trả lời kèm trích dẫn trang nguồn
- Upload catalog sản phẩm → hỏi "Thông số kỹ thuật đèn AT20?" → trả lời chính xác
- Upload 50 file hợp đồng → tìm kiếm điều khoản cụ thể trong tất cả hợp đồng

**Thông số hiện tại**:

| Thông số                   | Giá trị                                                  |
| -------------------------- | -------------------------------------------------------- |
| File tối đa mỗi lần upload | **2048 MB / file**                                       |
| Số file / lần upload       | **20 files**                                             |
| Định dạng hỗ trợ           | PDF, Word, Excel, CSV, TXT, MD, HTML, URL web, YouTube   |
| Ngôn ngữ tìm kiếm          | **50+ ngôn ngữ** (tiếng Việt, Anh, Trung, Nhật, v.v.)    |
| Phương thức tìm kiếm       | Kết hợp keyword + ngữ nghĩa (hybrid search)              |
| Bảo mật                    | Vectors lưu on-premise (PGVector). Text chunks gửi qua Gemini API để embedding |

**Khả năng xử lý**:

| Loại tài liệu              | Khả năng   | Thời gian ước tính |
| -------------------------- | ---------- | ------------------ |
| PDF 10 trang               | ✅ Rất tốt | < 10 giây          |
| PDF 100 trang (~50,000 từ) | ✅ Tốt     | 30-60 giây         |
| PDF 500 trang              | ✅ Khả thi | 2-5 phút           |
| File > 100 MB              | ✅ Khả thi | 3-10 phút          |
| 20 files cùng lúc          | ✅ Tốt     | Xử lý tuần tự      |

### 3.5. Xuất dữ liệu (Custom Tools)

Người dùng có thể xuất nội dung hội thoại thành file chuyên nghiệp:

| Công cụ        | Mô tả                                                              | Cách dùng                   |
| -------------- | ------------------------------------------------------------------ | --------------------------- |
| **Xuất Excel** | Trích xuất bảng biểu → file .xlsx có format, filter, freeze header | Nhấn icon ⚡ → "Xuất Excel" |
| **Xuất PDF**   | Xuất toàn bộ hội thoại → file PDF                                  | Nhấn icon ⚡ → "Xuất PDF"   |
| **Xuất Word**  | Xuất hội thoại → file .docx                                        | Nhấn icon ⚡ → "Xuất DOCX"  |

> 💡 Tool Excel đặc biệt: tự nhận dạng số, ngày tháng, phần trăm, tiền tệ VNĐ/$/€ và format đúng trong Excel.

---

## 4. QUẢN TRỊ HỆ THỐNG

### 4.1. Kiểm soát chi phí

Mỗi lần user gửi prompt đều phát sinh chi phí API. Hệ thống kiểm soát qua:

| Cơ chế                   | Mô tả                                                                                   |
| ------------------------ | --------------------------------------------------------------------------------------- |
| **Quota / user / tháng** | Mỗi user có hạn mức chi phí (USD). Hết quota → từ chối thêm                             |
| **Sub-keys API**         | Mỗi user/nhóm có key riêng, dễ quản lý                                                  |
| **Log chi tiết**         | Ghi lại EVERY request: user nào, model nào, bao nhiêu tokens, cost bao nhiêu            |
| **Bảng giá model**       | Mỗi model có giá riêng (input/output tokens), cập nhật trong DB (backup: `prices.json`) |
| **Dashboard**            | Xem báo cáo trực quan: chi phí theo user, theo model, theo ngày/tuần/tháng              |

### 4.2. Dashboard quản trị chi phí

Truy cập: `http://<server>:5000/dashboard`

Cung cấp thông tin:
- 📊 **Tổng chi phí** theo khoảng thời gian (ngày/tuần/tháng)
- 👤 **Chi phí theo từng user** – ai dùng nhiều nhất
- 🤖 **Chi phí theo model** – model nào tốn nhất
- 📈 **Xu hướng sử dụng** theo thời gian
- 📋 **Log request chi tiết** – trace từng request

### 4.3. Quản lý người dùng

| Thao tác              | Cách thực hiện                                            |
| --------------------- | --------------------------------------------------------- |
| Xem danh sách user    | Dashboard → Users tab                                     |
| **Tạo user mới**      | Dashboard → Users → ➕ Add User → Điền form → Copy subkey |
| **Sửa user**          | Dashboard → Users → ✏️ Edit → Sửa quota/model/role        |
| **Xóa user**          | Dashboard → Users → 🗑️ Delete → Confirm 2 lần             |
| **Rotate subkey**     | Dashboard → Users → 🔑 → Copy key mới                     |
| **Enable/Disable**    | Dashboard → Users → 🔴/🟢 toggle                          |
| Duyệt user Open WebUI | Admin Panel → Users → Approve                             |
| Xem lịch sử hoạt động | Dashboard → Logs tab hoặc Access tab                      |

### 4.4. Quản lý mô hình AI

| Thao tác                 | Mô tả                                               |
| ------------------------ | --------------------------------------------------- |
| Bật / tắt model          | Admin chọn model nào hiển thị cho user              |
| Giới hạn model theo user | Chỉ cho phép nhóm nào dùng model đắt tiền           |
| Cấu hình mặc định        | Set temperature, max_tokens mặc định cho từng model |
| Gán Knowledge vào model  | Model tự động tham chiếu tài liệu cụ thể            |

### 4.5. Quản lý cơ sở tri thức (Knowledge)

| Thao tác                 | Mô tả                                   |
| ------------------------ | --------------------------------------- |
| Tạo Knowledge Collection | Workspace → Knowledge → Create          |
| Upload tài liệu          | Kéo thả file (PDF, Word, Excel, v.v.)   |
| Phân quyền               | Chỉ cho phép user/nhóm cụ thể truy cập  |
| Xoá tài liệu             | Xoá file → tự động xoá vector tương ứng |
| Gán vào model            | Để model tự động có context từ tài liệu |

---

## 5. BẢO MẬT

### 5.1. Các lớp bảo mật hiện có

| Lớp               | Chi tiết                                                                  |
| ----------------- | ------------------------------------------------------------------------- |
| **Xác thực**      | Đăng nhập email/password + JWT token. Hỗ trợ OAuth/SSO (chưa kích hoạt)   |
| **Phân quyền**    | Role-based: Admin / User / Pending. Access control trên Knowledge + Model |
| **API Security**  | Sub-keys riêng cho từng user/nhóm. Middleware validate mọi request        |
| **Network**       | Docker internal network – các service nội bộ không expose ra ngoài        |
| **Dữ liệu**       | PostgreSQL lưu local trong Docker volume. Backup thủ công qua `pg_dump`   |
| **RAG Embedding** | Text chunks gửi tới **Google Gemini API** để chuyển thành vectors. Vectors lưu on-premise trong PGVector |
| **Firewall**      | Chỉ mở port 3000 (Nginx HTTPS), các port nội bộ đều đóng                                                |

### 5.2. Lưu ý bảo mật

- ⚠️ Nội dung chat **sẽ gửi** tới OpenAI/Google/xAI/Anthropic qua API để xử lý (đây là bản chất của dịch vụ LLM cloud)
- ⚠️ Text chunks từ tài liệu upload **sẽ gửi** tới Google Gemini API để tạo embedding vectors
- ✅ Vectors và tài liệu gốc **lưu trên máy chủ riêng** (PGVector on-premise)
- ✅ Database **lưu trên máy chủ riêng**, không dùng cloud database

---

## 6. CHI PHÍ VẬN HÀNH

### 6.1. Chi phí cố định (hạ tầng)

| Hạng mục | Chi phí                 | Ghi chú                                                         |
| -------- | ----------------------- | --------------------------------------------------------------- |
| Máy chủ  | Chi phí máy chủ hiện có | Windows Server đang sử dụng                                     |
| Phần mềm | **$0**                  | Open WebUI, LiteLLM, PostgreSQL – tất cả miễn phí (open source) |
| Docker   | **$0**                  | Docker CE miễn phí                                              |

### 6.2. Chi phí biến phí (API)

Chi phí phụ thuộc vào mức độ sử dụng, tính theo token (đơn vị đo lường text AI xử lý):

| Model            | Giá input     | Giá output     | Ước tính / 1 cuộc chat |
| ---------------- | ------------- | -------------- | ---------------------- |
| GPT-5            | ~$5/1M tokens | ~$15/1M tokens | ~$0.01-0.05            |
| GPT-4o Mini      | ~$0.15/1M     | ~$0.60/1M      | ~$0.001-0.005          |
| Gemini 2.5 Flash | ~$0.075/1M    | ~$0.30/1M      | ~$0.0005-0.002         |
| DALL-E 3 (ảnh)   | —             | —              | ~$0.04/ảnh             |

> 💡 **Ước tính**: Với 10 nhân viên dùng bình thường (~20 requests/ngày), chi phí khoảng **$50-150/tháng**.

### 6.3. Kiểm soát chi phí

- Mỗi user được cấp **quota (hạn mức)** hàng tháng
- Vượt quota → hệ thống **tự động từ chối** request
- Admin xem báo cáo chi phí bất kỳ lúc nào trên Dashboard
- Có thể điều chỉnh quota theo vai trò: quản lý cao hơn, nhân viên thấp hơn

---

## 7. HƯỚNG DẪN NHANH CHO QUẢN TRỊ VIÊN

### 7.1. Thao tác hàng ngày

| STT | Thao tác          | Cách làm                                     |
| --- | ----------------- | -------------------------------------------- |
| 1   | Duyệt user mới    | Admin Panel → Users → Approve pending users  |
| 2   | Kiểm tra chi phí  | Dashboard (`http://<server>:5000/dashboard`) |
| 3   | Xem log hoạt động | Dashboard → Logs tab                         |

### 7.2. Thao tác hàng tuần

| STT | Thao tác                      | Cách làm                                                                             |
| --- | ----------------------------- | ------------------------------------------------------------------------------------ |
| 1   | Review chi phí theo user      | Dashboard → Filter by user                                                           |
| 2   | Kiểm tra sức khoẻ hệ thống    | `docker compose ps` xem tất cả container running                                     |
| 3   | Backup database (khuyến nghị) | `docker exec openwebui-postgres pg_dump -U openwebui_user -d openwebui > backup.sql` |

### 7.3. Thao tác khi cần

| STT | Tình huống           | Cách xử lý                                                                             |
| --- | -------------------- | -------------------------------------------------------------------------------------- |
| 1   | User quên mật khẩu   | Admin → Users → Reset Password                                                         |
| 2   | Container bị dừng    | `docker compose up -d` tại thư mục dự án                                               |
| 3   | Cần thêm model mới   | Sửa `litellm/litellm_config.yaml` → `docker compose restart litellm`                   |
| 4   | Tăng quota cho user  | Dashboard → Users tab → chỉnh quota, hoặc API `PATCH /v1/_mw/admin/users/{user_id}`    |
| 5   | Upload file quá 50MB | Sửa `RAG_FILE_MAX_SIZE` trong `docker-compose.yml` → `docker compose up -d open-webui` |

---

## 8. KẾ HOẠCH PHÁT TRIỂN

### 8.1. Ngắn hạn (1-2 tháng)

| #   | Hạng mục                 | Ưu tiên       | Kết quả kỳ vọng                                                             |
| --- | ------------------------ | ------------- | --------------------------------------------------------------------------- |
| 1   | **Nhóm người dùng**      | 🔴 Cao        | Phân nhóm theo phòng ban, gán quyền và quota theo nhóm thay vì từng cá nhân |
| 2   | **Backup tự động**       | 🔴 Cao        | Tự động backup database hàng ngày, giảm rủi ro mất dữ liệu                  |
| 3   | **Prompt Templates**     | 🟡 Trung bình | Tạo mẫu prompt sẵn cho các tác vụ phổ biến (báo giá, phân tích, báo cáo)    |
| 4   | **Hướng dẫn người dùng** | 🟡 Trung bình | Tài liệu/video hướng dẫn cho end-user                                       |

### 8.2. Trung hạn (3-6 tháng)

| #   | Hạng mục                    | Kết quả kỳ vọng                                                                  |
| --- | --------------------------- | -------------------------------------------------------------------------------- |
| 1   | **SSO/LDAP**                | Đăng nhập bằng tài khoản công ty, không cần tạo tài khoản riêng                  |
| 2   | **Monitoring & Alerting**   | Dashboard giám sát realtime, cảnh báo khi hệ thống có vấn đề                     |
| 3   | **API integration**         | Kết nối với DMS, ERP, CRM nội bộ – AI hỗ trợ trực tiếp trong quy trình nghiệp vụ |
| 4   | **Báo cáo chi phí tự động** | Email/Zalo báo cáo chi phí hàng tuần tự động gửi đến quản lý                     |

### 8.3. Dài hạn (6-12 tháng)

| #   | Hạng mục           | Kết quả kỳ vọng                                                            |
| --- | ------------------ | -------------------------------------------------------------------------- |
| 1   | **On-premise LLM** | Chạy AI local (Llama, Mistral) – 100% dữ liệu không ra ngoài, giảm phí API |
| 2   | **Fine-tuning**    | Huấn luyện model riêng trên dữ liệu công ty – AI hiểu sâu nghiệp vụ        |
| 3   | **Multi-tenant**   | Mở rộng phục vụ nhiều đơn vị/chi nhánh trên cùng hạ tầng                   |

---

## 9. SO SÁNH VỚI GIẢI PHÁP KHÁC

| Tiêu chí          | ChatGPT Enterprise      | Hệ thống hiện tại (Open WebUI)      |
| ----------------- | ----------------------- | ----------------------------------- |
| Chi phí cố định   | ~$30/user/tháng         | **$0** (open source)                |
| Chi phí API       | Gộp trong gói           | Theo thực tế sử dụng                |
| Kiểm soát chi phí | Giới hạn theo gói       | **Tùy chỉnh quota từng user**       |
| Bảo mật dữ liệu   | Cloud (Microsoft Azure) | **Server riêng**                    |
| RAG / Knowledge   | Có                      | **Có** (PGVector + local embedding) |
| Đa model          | Chỉ OpenAI              | **4 providers** (19 models)         |
| Custom tools      | Giới hạn                | **Tuỳ chỉnh hoàn toàn** (Python)    |
| Tạo ảnh           | Có (DALL-E 3)           | **Có** (DALL-E 3 + Gemini)          |
| Giọng nói         | Có                      | **Có** (TTS + STT)                  |
| Deploy            | Cloud only              | **On-premise** (Docker)             |

---

## 10. PHỤ LỤC

### 10.1. Danh sách 19 mô hình AI sẵn sàng

| #   | Model                      | Nhà cung cấp | Loại | Mô tả ngắn               |
| --- | -------------------------- | ------------ | ---- | ------------------------ |
| 1   | chat-gpt-5.4               | OpenAI       | Chat | Flagship, reasoning mạnh |
| 2   | chat-gpt-5.2               | OpenAI       | Chat | Cân bằng                 |
| 3   | chat-gpt-5                 | OpenAI       | Chat | Tiêu chuẩn               |
| 4   | chat-gemini-3.1-pro-preview| Google       | Chat | Flagship Google          |
| 5   | chat-gemini-3.1-flash-lite-preview | Google | Chat | Nhanh, rẻ              |
| 6   | chat-gemini-2.5-flash      | Google       | Chat | Cân bằng, tiếng Việt tốt |
| 7   | chat-grok-4.20-reasoning   | xAI          | Chat | Reasoning mạnh           |
| 8   | chat-grok-4-1-fast-reasoning | xAI        | Chat | Nhanh, reasoning         |
| 9   | chat-grok-4-1-fast-non-reasoning | xAI    | Chat | Nhanh nhất, rẻ           |
| 10  | chat-claude-opus-4.6       | Anthropic    | Chat | Flagship Anthropic       |
| 11  | chat-claude-sonnet-4.6     | Anthropic    | Chat | Cân bằng                 |
| 12  | chat-claude-haiku-4.5      | Anthropic    | Chat | Nhanh, rẻ                |
| 13  | img-gpt-image-1.5          | OpenAI       | Ảnh  | Mới nhất, 4x nhanh hơn   |
| 14  | img-gpt-image-1            | OpenAI       | Ảnh  | Chất lượng cao           |
| 15  | img-gemini-3.1-flash       | Google       | Ảnh  | Tạo ảnh nhanh            |
| 16  | img-gemini-3-pro           | Google       | Ảnh  | Ảnh chất lượng cao       |
| 17  | img-grok-imagine           | xAI          | Ảnh  | Tiêu chuẩn               |
| 18  | img-grok-imagine-pro       | xAI          | Ảnh  | Chất lượng cao           |
| 19  | gemini-embedding-001       | Google       | Embed| 1536-dim (giảm từ 3072)  |

### 10.2. Thông tin truy cập

| Dịch vụ                      | URL                                            | Ghi chú               |
| ---------------------------- | ---------------------------------------------- | --------------------- |
| Open WebUI (giao diện chính) | `https://<server>:3000`                        | Qua Nginx HTTPS       |
| Middleware Dashboard         | `https://<server>:3000/dashboard`              | Chỉ Admin, qua Nginx  |
| API Endpoint                 | `https://<server>:3000/v1/_mw/`                | Cho tích hợp ứng dụng |

### 10.3. File cấu hình quan trọng

| File                          | Mục đích                                | Khi nào cần sửa                       |
| ----------------------------- | --------------------------------------- | ------------------------------------- |
| `docker-compose.yml`          | Cấu hình toàn bộ hệ thống, DATABASE_URL | Đổi model, tăng file upload, đổi port |
| `.env`                        | API keys, mật khẩu                      | Đổi API key, mật khẩu DB              |
| `litellm/litellm_config.yaml` | Danh sách model AI                      | Thêm/bớt model                        |

> **Lưu ý:** Dữ liệu users, prices, quota, logs giờ đây lưu trong PostgreSQL (database `middleware`). File `users.json`, `prices.json` vẫn được ghi backup nhưng **DB là nguồn chính**. Quản lý qua Dashboard hoặc API.

### 10.4. Tài liệu kỹ thuật chi tiết

Để tìm hiểu thêm về các khía cạnh kỹ thuật, xem:
- `docs/rag-architecture.md` – Kiến trúc RAG chi tiết
- `docs/database-architecture.md` – Database schema chi tiết (32 tables)
- `docs/checklist-tinh-nang.md` – Checklist 110+ tính năng (version markdown)
- `docs/List function.xlsx` – Checklist tính năng (version Excel)
- `docs/ARCHITECTURE.md` – Kiến trúc Middleware
- `docs/USER_GUIDE_VI.md` – Hướng dẫn người dùng
- `docs/USER_MANAGEMENT.md` – Quản lý người dùng

---

*Tài liệu này được cập nhật ngày 2026-03-03. Liên hệ đội kỹ thuật AI để biết thêm chi tiết.*
