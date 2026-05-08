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

| # | Giá trị                    | Mô tả chi tiết                                                                                                                                              |
| - | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | **Tiết kiệm chi phí**      | Một tài khoản API, kiểm soát quota từng người, tránh chi phí phát sinh ngoài kế hoạch                                                                       |
| 2 | **Bảo mật dữ liệu nội bộ** | Tài liệu nội bộ lưu trên server riêng, vectors lưu on-premise trong PGVector. Embedding qua Gemini API (text chunks gửi qua Google để chuyển thành vectors) |
| 3 | **Năng suất nhân viên**    | Hỗ trợ soạn thảo, phân tích, báo cáo, dịch thuật, tra cứu – tiết kiệm 30-50% thời gian thao tác lặp                                                         |
| 4 | **Tri thức tập trung**     | Upload tài liệu nội bộ → AI trả lời dựa trên chính sách, quy trình thực tế của công ty                                                                      |
| 5 | **Đa phương thức**         | Không chỉ chat text – còn tạo ảnh, nhận dạng giọng nói, đọc tài liệu, xuất Excel/PDF                                                                        |
| 6 | **Quản trị minh bạch**     | Theo dõi ai dùng gì, tốn bao nhiêu, thống kê chi phí theo thời gian                                                                                         |

### Số liệu nổi bật

| STT | Chỉ số                            | Giá trị                                                   |
| --- | --------------------------------- | --------------------------------------------------------- |
| 01  | Tổng số mô hình AI sẵn sàng       | **19** (12 chat + 6 ảnh + 1 embedding)                    |
| 02  | Nhà cung cấp AI                   | **4** – OpenAI, Google Gemini, xAI Grok, Anthropic Claude |
| 03  | Tổng tính năng đã hoạt động       | **116**                                                   |
| 04  | Tính năng trong kế hoạch          | **12**                                                    |
| 05  | Dung lượng file upload RAG tối đa | **2048 MB / file**                                        |
| 06  | Ngôn ngữ hỗ trợ (AI + RAG)        | **50+ ngôn ngữ** (bao gồm tiếng Việt)                     |
| 07  | Thời gian triển khai              | **Docker Compose – khởi động trong 2 phút**               |

---

## 2. TÌNH TRẠNG HIỆN TẠI CỦA HỆ THỐNG

### 2.1. Trạng thái vận hành

| STT | Thành phần                   | Trạng thái      | Ghi chú                                   |
| --- | ---------------------------- | --------------- | ----------------------------------------- |
| 01  | 🟢 Giao diện web (Open WebUI) | **Hoạt động**   | Truy cập qua HTTPS (Nginx :3000)          |
| 02  | 🟢 Middleware (Auth + Quota)  | **Hoạt động**   | Kiểm soát chi phí, phân quyền             |
| 03  | 🟢 LiteLLM (LLM Proxy)        | **Hoạt động**   | Kết nối OpenAI + Gemini + xAI + Anthropic |
| 04  | 🟢 PostgreSQL + PGVector      | **Hoạt động**   | Database + vector search                  |
| 05  | 🟢 Docling (OCR/Extract)      | **Hoạt động**   | Extract text từ PDF, DOCX                 |
| 06  | 🟢 Embedding qua Gemini API   | **Hoạt động**   | gemini-embedding-001, 1536-dim            |
| 07  | 🟢 Firewall mở port 3000      | **Đã cấu hình** | Truy cập qua Nginx HTTPS                  |

### 2.2. Người dùng

| STT | Phân loại   | Mô tả                                                                    |
| --- | ----------- | ------------------------------------------------------------------------ |
| 01  | **Admin**   | Toàn quyền quản trị: users, models, knowledge, settings, xem log chi phí |
| 02  | **User**    | Sử dụng chat AI, upload tài liệu, tạo knowledge cá nhân, xuất file       |
| 03  | **Pending** | Tài khoản đã đăng ký, chờ Admin duyệt mới được sử dụng                   |

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

| STT | Model                      | Nhà cung cấp | Mô tả                                |
| --- | -------------------------- | ------------ | ------------------------------------ |
| 01  | **GPT-Image-1.5** (OpenAI) | OpenAI       | Mới nhất, 4x nhanh hơn, 3 chất lượng |
| 02  | **GPT-Image-1** (OpenAI)   | OpenAI       | Chất lượng cao, 3 cấp độ             |
| 03  | **Gemini 3.1 Flash Image** | Google       | Tạo ảnh nhanh, chi phí thấp          |
| 04  | **Gemini 3 Pro Image**     | Google       | Chất lượng cao                       |
| 05  | **Grok Imagine**           | xAI          | Tiêu chuẩn, $0.05/ảnh                |
| 06  | **Grok Imagine Pro**       | xAI          | Chất lượng cao, $0.10/ảnh            |

### 3.3. Giọng nói

| STT | Tính năng          | Mô tả                  | Ứng dụng                                  |
| --- | ------------------ | ---------------------- | ----------------------------------------- |
| 01  | **Text-to-Speech** | AI đọc lại câu trả lời | Nghe báo cáo khi di chuyển                |
| 02  | **Speech-to-Text** | Nói thay vì gõ         | Nhập liệu nhanh, người không quen gõ phím |

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

| STT | Thông số                   | Giá trị                                                                        |
| --- | -------------------------- | ------------------------------------------------------------------------------ |
| 01  | File tối đa mỗi lần upload | **2048 MB / file**                                                             |
| 02  | Số file / lần upload       | **20 files**                                                                   |
| 03  | Định dạng hỗ trợ           | PDF, Word, Excel, CSV, TXT, MD, HTML, URL web, YouTube                         |
| 04  | Ngôn ngữ tìm kiếm          | **50+ ngôn ngữ** (tiếng Việt, Anh, Trung, Nhật, v.v.)                          |
| 05  | Phương thức tìm kiếm       | Kết hợp keyword + ngữ nghĩa (hybrid search)                                    |
| 06  | Bảo mật                    | Vectors lưu on-premise (PGVector). Text chunks gửi qua Gemini API để embedding |

**Khả năng xử lý**:

| STT | Loại tài liệu              | Khả năng  | Thời gian ước tính |
| --- | -------------------------- | --------- | ------------------ |
| 01  | PDF 10 trang               | ✅ Rất tốt | < 10 giây          |
| 02  | PDF 100 trang (~50,000 từ) | ✅ Tốt     | 30-60 giây         |
| 03  | PDF 500 trang              | ✅ Khả thi | 2-5 phút           |
| 04  | File > 100 MB              | ✅ Khả thi | 3-10 phút          |
| 05  | 20 files cùng lúc          | ✅ Tốt     | Xử lý tuần tự      |

### 3.5. Xuất dữ liệu (Custom Tools)

Người dùng có thể xuất nội dung hội thoại thành file chuyên nghiệp:

| STT | Công cụ        | Mô tả                                                              | Cách dùng                  |
| --- | -------------- | ------------------------------------------------------------------ | -------------------------- |
| 01  | **Xuất Excel** | Trích xuất bảng biểu → file .xlsx có format, filter, freeze header | Nhấn icon ⚡ → "Xuất Excel" |
| 02  | **Xuất PDF**   | Xuất toàn bộ hội thoại → file PDF                                  | Nhấn icon ⚡ → "Xuất PDF"   |
| 03  | **Xuất Word**  | Xuất hội thoại → file .docx                                        | Nhấn icon ⚡ → "Xuất DOCX"  |

> 💡 Tool Excel đặc biệt: tự nhận dạng số, ngày tháng, phần trăm, tiền tệ VNĐ/$/€ và format đúng trong Excel.

---

## 4. QUẢN TRỊ HỆ THỐNG

### 4.1. Kiểm soát chi phí

Mỗi lần user gửi prompt đều phát sinh chi phí API. Hệ thống kiểm soát qua:

| STT | Cơ chế                   | Mô tả                                                                                   |
| --- | ------------------------ | --------------------------------------------------------------------------------------- |
| 01  | **Quota / user / tháng** | Mỗi user có hạn mức chi phí (USD). Hết quota → từ chối thêm                             |
| 02  | **Sub-keys API**         | Mỗi user/nhóm có key riêng, dễ quản lý                                                  |
| 03  | **Log chi tiết**         | Ghi lại EVERY request: user nào, model nào, bao nhiêu tokens, cost bao nhiêu            |
| 04  | **Bảng giá model**       | Mỗi model có giá riêng (input/output tokens), cập nhật trong DB (backup: `prices.json`) |
| 05  | **Dashboard**            | Xem báo cáo trực quan: chi phí theo user, theo model, theo ngày/tuần/tháng              |

### 4.2. Dashboard quản trị chi phí

Truy cập: `https://openwebui.rangdong.com.vn:51122/dashboard`

Cung cấp thông tin:
- 📊 **Tổng chi phí** theo khoảng thời gian (ngày/tuần/tháng)
- 👤 **Chi phí theo từng user** – ai dùng nhiều nhất
- 🤖 **Chi phí theo model** – model nào tốn nhất
- 📈 **Xu hướng sử dụng** theo thời gian
- 📋 **Log request chi tiết** – trace từng request

### 4.3. Quản lý người dùng

| STT | Thao tác              | Cách thực hiện                                           |
| --- | --------------------- | -------------------------------------------------------- |
| 01  | Xem danh sách user    | Dashboard → Users tab                                    |
| 02  | **Tạo user mới**      | Dashboard → Users → ➕ Add User → Điền form → Copy subkey |
| 03  | **Sửa user**          | Dashboard → Users → ✏️ Edit → Sửa quota/model/role       |
| 04  | **Xóa user**          | Dashboard → Users → 🗑️ Delete → Confirm 2 lần            |
| 05  | **Rotate subkey**     | Dashboard → Users → 🔑 → Copy key mới                     |
| 06  | **Enable/Disable**    | Dashboard → Users → 🔴/🟢 toggle                           |
| 07  | Duyệt user Open WebUI | Admin Panel → Users → Approve                            |
| 08  | Xem lịch sử hoạt động | Dashboard → Logs tab hoặc Access tab                     |

### 4.4. Quản lý mô hình AI

| STT | Thao tác                 | Mô tả                                               |
| --- | ------------------------ | --------------------------------------------------- |
| 01  | Bật / tắt model          | Admin chọn model nào hiển thị cho user              |
| 02  | Giới hạn model theo user | Chỉ cho phép nhóm nào dùng model đắt tiền           |
| 03  | Cấu hình mặc định        | Set temperature, max_tokens mặc định cho từng model |
| 04  | Gán Knowledge vào model  | Model tự động tham chiếu tài liệu cụ thể            |

### 4.5. Quản lý cơ sở tri thức (Knowledge)

| STT | Thao tác                 | Mô tả                                   |
| --- | ------------------------ | --------------------------------------- |
| 01  | Tạo Knowledge Collection | Workspace → Knowledge → Create          |
| 02  | Upload tài liệu          | Kéo thả file (PDF, Word, Excel, v.v.)   |
| 03  | Phân quyền               | Chỉ cho phép user/nhóm cụ thể truy cập  |
| 04  | Xoá tài liệu             | Xoá file → tự động xoá vector tương ứng |
| 05  | Gán vào model            | Để model tự động có context từ tài liệu |

---

## 5. BẢO MẬT

### 5.1. Các lớp bảo mật hiện có

| STT | Lớp               | Chi tiết                                                                                                 |
| --- | ----------------- | -------------------------------------------------------------------------------------------------------- |
| 01  | **Xác thực**      | Đăng nhập email/password + JWT token. Hỗ trợ OAuth/SSO (chưa kích hoạt)                                  |
| 02  | **Phân quyền**    | Role-based: Admin / User / Pending. Access control trên Knowledge + Model                                |
| 03  | **API Security**  | Sub-keys riêng cho từng user/nhóm. Middleware validate mọi request                                       |
| 04  | **Network**       | Docker internal network – các service nội bộ không expose ra ngoài                                       |
| 05  | **Dữ liệu**       | PostgreSQL lưu local trong Docker volume. Backup thủ công qua `pg_dump`                                  |
| 06  | **RAG Embedding** | Text chunks gửi tới **Google Gemini API** để chuyển thành vectors. Vectors lưu on-premise trong PGVector |
| 07  | **Firewall**      | Chỉ mở port 3000 (Nginx HTTPS), các port nội bộ đều đóng                                                 |

### 5.2. Lưu ý bảo mật

- ⚠️ Nội dung chat **sẽ gửi** tới OpenAI/Google/xAI/Anthropic qua API để xử lý (đây là bản chất của dịch vụ LLM cloud)
- ⚠️ Text chunks từ tài liệu upload **sẽ gửi** tới Google Gemini API để tạo embedding vectors
- ✅ Vectors và tài liệu gốc **lưu trên máy chủ riêng** (PGVector on-premise)
- ✅ Database **lưu trên máy chủ riêng**, không dùng cloud database

---

## 6. CHI PHÍ VẬN HÀNH

### 6.1. Chi phí cố định (hạ tầng)

| STT | Hạng mục | Chi phí                 | Ghi chú                                                         |
| --- | -------- | ----------------------- | --------------------------------------------------------------- |
| 01  | Máy chủ  | Chi phí máy chủ hiện có | Windows Server đang sử dụng                                     |
| 02  | Phần mềm | **$0**                  | Open WebUI, LiteLLM, PostgreSQL – tất cả miễn phí (open source) |
| 03  | Docker   | **$0**                  | Docker CE miễn phí                                              |

### 6.2. Chi phí biến phí (API)

Chi phí phụ thuộc vào mức độ sử dụng, tính theo token (đơn vị đo lường text AI xử lý):

| STT | Model            | Giá input     | Giá output     | Ước tính / 1 cuộc chat |
| --- | ---------------- | ------------- | -------------- | ---------------------- |
| 01  | GPT-5            | ~$5/1M tokens | ~$15/1M tokens | ~$0.01-0.05            |
| 02  | GPT-4o Mini      | ~$0.15/1M     | ~$0.60/1M      | ~$0.001-0.005          |
| 03  | Gemini 2.5 Flash | ~$0.075/1M    | ~$0.30/1M      | ~$0.0005-0.002         |
| 04  | DALL-E 3 (ảnh)   | —             | —              | ~$0.04/ảnh             |

> 💡 **Ước tính**: Với 10 nhân viên dùng bình thường (~20 requests/ngày), chi phí khoảng **$50-150/tháng**.

### 6.3. Kiểm soát chi phí

- Mỗi user được cấp **quota (hạn mức)** hàng tháng
- Vượt quota → hệ thống **tự động từ chối** request
- Admin xem báo cáo chi phí bất kỳ lúc nào trên Dashboard
- Có thể điều chỉnh quota theo vai trò: quản lý cao hơn, nhân viên thấp hơn

---

## 7. HƯỚNG DẪN NHANH CHO QUẢN TRỊ VIÊN

### 7.1. Thao tác hàng ngày

| STT | Thao tác          | Cách làm                                                        |
| --- | ----------------- | --------------------------------------------------------------- |
| 1   | Duyệt user mới    | Admin Panel → Users → Approve pending users                     |
| 2   | Kiểm tra chi phí  | Dashboard (`https://openwebui.rangdong.com.vn:51122/dashboard`) |
| 3   | Xem log hoạt động | Dashboard → Logs tab                                            |

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

| # | Hạng mục                 | Ưu tiên      | Kết quả kỳ vọng                                                             |
| - | ------------------------ | ------------ | --------------------------------------------------------------------------- |
| 1 | **Nhóm người dùng**      | 🔴 Cao        | Phân nhóm theo phòng ban, gán quyền và quota theo nhóm thay vì từng cá nhân |
| 2 | **Backup tự động**       | 🔴 Cao        | Tự động backup database hàng ngày, giảm rủi ro mất dữ liệu                  |
| 3 | **Prompt Templates**     | 🟡 Trung bình | Tạo mẫu prompt sẵn cho các tác vụ phổ biến (báo giá, phân tích, báo cáo)    |
| 4 | **Hướng dẫn người dùng** | 🟡 Trung bình | Tài liệu/video hướng dẫn cho end-user                                       |

### 8.2. Trung hạn (3-6 tháng)

| # | Hạng mục                    | Kết quả kỳ vọng                                                                  |
| - | --------------------------- | -------------------------------------------------------------------------------- |
| 1 | **SSO/LDAP**                | Đăng nhập bằng tài khoản công ty, không cần tạo tài khoản riêng                  |
| 2 | **Monitoring & Alerting**   | Dashboard giám sát realtime, cảnh báo khi hệ thống có vấn đề                     |
| 3 | **API integration**         | Kết nối với DMS, ERP, CRM nội bộ – AI hỗ trợ trực tiếp trong quy trình nghiệp vụ |
| 4 | **Báo cáo chi phí tự động** | Email/Zalo báo cáo chi phí hàng tuần tự động gửi đến quản lý                     |

### 8.3. Dài hạn (6-12 tháng)

| # | Hạng mục           | Kết quả kỳ vọng                                                            |
| - | ------------------ | -------------------------------------------------------------------------- |
| 1 | **On-premise LLM** | Chạy AI local (Llama, Mistral) – 100% dữ liệu không ra ngoài, giảm phí API |
| 2 | **Fine-tuning**    | Huấn luyện model riêng trên dữ liệu công ty – AI hiểu sâu nghiệp vụ        |
| 3 | **Multi-tenant**   | Mở rộng phục vụ nhiều đơn vị/chi nhánh trên cùng hạ tầng                   |

---

## 9. SO SÁNH VỚI GIẢI PHÁP KHÁC

| STT | Tiêu chí          | ChatGPT Enterprise      | Hệ thống hiện tại (Open WebUI)      |
| --- | ----------------- | ----------------------- | ----------------------------------- |
| 01  | Chi phí cố định   | ~$30/user/tháng         | **$0** (open source)                |
| 02  | Chi phí API       | Gộp trong gói           | Theo thực tế sử dụng                |
| 03  | Kiểm soát chi phí | Giới hạn theo gói       | **Tùy chỉnh quota từng user**       |
| 04  | Bảo mật dữ liệu   | Cloud (Microsoft Azure) | **Server riêng**                    |
| 05  | RAG / Knowledge   | Có                      | **Có** (PGVector + local embedding) |
| 06  | Đa model          | Chỉ OpenAI              | **4 providers** (19 models)         |
| 07  | Custom tools      | Giới hạn                | **Tuỳ chỉnh hoàn toàn** (Python)    |
| 08  | Tạo ảnh           | Có (DALL-E 3)           | **Có** (DALL-E 3 + Gemini)          |
| 09  | Giọng nói         | Có                      | **Có** (TTS + STT)                  |
| 10  | Deploy            | Cloud only              | **On-premise** (Docker)             |

---

## 10. PHỤ LỤC

### 10.1. Danh sách 19 mô hình AI sẵn sàng

| #  | Model                              | Nhà cung cấp | Loại  | Mô tả ngắn               |
| -- | ---------------------------------- | ------------ | ----- | ------------------------ |
| 1  | chat-gpt-5.4                       | OpenAI       | Chat  | Flagship, reasoning mạnh |
| 2  | chat-gpt-5.2                       | OpenAI       | Chat  | Cân bằng                 |
| 3  | chat-gpt-5                         | OpenAI       | Chat  | Tiêu chuẩn               |
| 4  | chat-gemini-3.1-pro-preview        | Google       | Chat  | Flagship Google          |
| 5  | chat-gemini-3.1-flash-lite-preview | Google       | Chat  | Nhanh, rẻ                |
| 6  | chat-gemini-2.5-flash              | Google       | Chat  | Cân bằng, tiếng Việt tốt |
| 7  | chat-grok-4.20                     | xAI          | Chat  | Reasoning mạnh           |
| 8  | chat-grok-4.1-fast                 | xAI          | Chat  | Nhanh, reasoning         |
| 9  | chat-grok-4.1-fast-lite            | xAI          | Chat  | Nhanh nhất, rẻ           |
| 10 | chat-claude-opus-4.6               | Anthropic    | Chat  | Flagship Anthropic       |
| 11 | chat-claude-sonnet-4.6             | Anthropic    | Chat  | Cân bằng                 |
| 12 | chat-claude-haiku-4.5              | Anthropic    | Chat  | Nhanh, rẻ                |
| 13 | img-gpt-1.5                        | OpenAI       | Ảnh   | Mới nhất, 4x nhanh hơn   |
| 14 | img-gpt-1                          | OpenAI       | Ảnh   | Chất lượng cao           |
| 15 | img-gemini-3.1-flash               | Google       | Ảnh   | Tạo ảnh nhanh            |
| 16 | img-gemini-3-pro                   | Google       | Ảnh   | Ảnh chất lượng cao       |
| 17 | img-grok-imagine                   | xAI          | Ảnh   | Tiêu chuẩn               |
| 18 | img-grok-imagine-pro               | xAI          | Ảnh   | Chất lượng cao           |
| 19 | gemini-embedding-001               | Google       | Embed | 1536-dim (giảm từ 3072)  |

### 10.2. Thông tin truy cập

| STT | Dịch vụ                      | URL                                                 | Ghi chú               |
| --- | ---------------------------- | --------------------------------------------------- | --------------------- |
| 01  | Open WebUI (giao diện chính) | `https://openwebui.rangdong.com.vn:51122`           | Qua Nginx HTTPS       |
| 02  | Middleware Dashboard         | `https://openwebui.rangdong.com.vn:51122/dashboard` | Chỉ Admin, qua Nginx  |
| 03  | API Endpoint                 | `https://openwebui.rangdong.com.vn:51122/v1/_mw/`   | Cho tích hợp ứng dụng |

### 10.3. File cấu hình quan trọng

| STT | File                          | Mục đích                                | Khi nào cần sửa                       |
| --- | ----------------------------- | --------------------------------------- | ------------------------------------- |
| 01  | `docker-compose.yml`          | Cấu hình toàn bộ hệ thống, DATABASE_URL | Đổi model, tăng file upload, đổi port |
| 02  | `.env`                        | API keys, mật khẩu                      | Đổi API key, mật khẩu DB              |
| 03  | `litellm/litellm_config.yaml` | Danh sách model AI                      | Thêm/bớt model                        |

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
