# FORM KIỂM THỬ TÍNH NĂNG - OPEN WEBUI
> **Phiên bản**: v1.0  
> **Ngày tạo**: 2026-04-01  
> **Hệ thống**: Open WebUI + LiteLLM + Middleware + PostgreSQL/PGVector  
> **URL**: https://openwebui.example.com  

---

## HƯỚNG DẪN SỬ DỤNG FORM TEST

| Ký hiệu | Ý nghĩa |
|----------|----------|
| ✅ PASS | Tính năng hoạt động đúng kỳ vọng |
| ❌ FAIL | Tính năng không hoạt động hoặc sai kỳ vọng |
| ⚠️ PARTIAL | Hoạt động một phần, cần ghi chú chi tiết |
| ⏳ SKIP | Chưa test / Bỏ qua |

**Người test điền vào các cột**: `Kết quả`, `Câu trả lời thực tế`, `Đánh giá (1-5)`, `Ghi chú / Bug`

---

## PHẦN A: TÍNH NĂNG NGƯỜI DÙNG (USER)

---

### A1. HỎI ĐÁP (CHAT AI)

#### A1.1 Chất lượng trả lời

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 1 | Trả lời tiếng Việt | Hỏi: "Giải thích nguyên lý hoạt động của pin mặt trời" | Trả lời mượt mà bằng tiếng Việt, nội dung chính xác, không lỗi ngữ pháp | | | | |
| 2 | Trả lời tiếng Anh | Hỏi: "Explain how LED lighting works" | Trả lời tiếng Anh chính xác, ngữ pháp tốt | | | | |
| 3 | Trả lời chuyên ngành | Hỏi: "So sánh ưu nhược điểm của đèn LED và đèn huỳnh quang trong chiếu sáng công nghiệp" | Thông tin chuyên ngành chính xác, có so sánh rõ ràng | | | | |
| 4 | Trả lời có số liệu | Hỏi: "Dân số Việt Nam năm 2025 là bao nhiêu?" | Số liệu gần đúng, có ghi nguồn hoặc disclaimer | | | | |
| 5 | Trả lời dạng bảng | Hỏi: "Lập bảng so sánh 5 loại đèn LED phổ biến theo công suất, tuổi thọ, giá" | Hiển thị bảng markdown đẹp, dữ liệu hợp lý | | | | |
| 6 | Trả lời dạng code | Hỏi: "Viết code Python đọc file Excel và vẽ biểu đồ" | Code chạy được, có syntax highlighting | | | | |
| 7 | Hội thoại nhiều lượt | Hỏi 3-4 câu liên tiếp về cùng 1 chủ đề, câu sau liên quan câu trước | AI nhớ context, trả lời liên tục mạch lạc | | | | |
| 8 | Streaming response | Quan sát khi AI trả lời | Text hiển thị từng token, không bị giật lag | | | | |

#### A1.2 Chức năng hội thoại (Functions)

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 9 | Tạo hội thoại mới | Nhấn nút "New Chat" | Mở chat mới, không còn context cũ | | | | |
| 10 | Xóa hội thoại | Xóa 1 hội thoại từ sidebar | Hội thoại bị xóa, không còn trong danh sách | | | | |
| 11 | Xóa nhiều hội thoại | Xóa 3 hội thoại cùng lúc | Tất cả bị xóa thành công | | | | |
| 12 | Đổi tên hội thoại | Click vào tên hội thoại → Sửa tên | Tên mới được lưu, hiển thị đúng | | | | |
| 13 | Pin hội thoại | Ghim 1 hội thoại | Hội thoại được đóng ghim, hiển thị ở đầu | | | | |
| 14 | Archive hội thoại | Lưu trữ 1 hội thoại | Hội thoại chuyển vào mục Archive | | | | |
| 15 | Tạo folder | Tạo folder mới trong sidebar | Folder được tạo, có thể kéo thả chat vào | | | | |
| 16 | Tìm kiếm chat | Gõ keyword vào thanh search | Tìm được hội thoại chứa keyword | | | | |
| 17 | Chia sẻ hội thoại | Nhấn Share → Copy link | Link được tạo, người khác mở được | | | | |
| 18 | Xuất file Excel | Action → "Xuất Excel" | File .xlsx tải về, có format, filter, dữ liệu đúng | | | | |
| 19 | Xuất file PDF | Action → "Xuất PDF" | File .pdf tải về, nội dung đúng, format đẹp | | | | |
| 20 | Xuất file DOCX | Action → "Xuất DOCX" | File .docx tải về, nội dung đúng | | | | |
| 21 | Tags | Gắn tag cho hội thoại | Tag được lưu, lọc theo tag hoạt động | | | | |

---

### A2. TẠO ẢNH AI (IMAGE GENERATION)

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 22 | Tạo ảnh cơ bản (DALL-E 3) | Chọn model `img-gpt-dalle-3`, gõ: "Vẽ một con mèo đang ngồi trên bàn làm việc" | Ảnh được tạo, hiển thị đúng mô tả | | | | |
| 23 | Tạo ảnh Gemini Flash | Chọn model `img-gemini-flash`, gõ: "Logo công ty công nghệ xanh hiện đại" | Ảnh được tạo nhanh, chất lượng OK | | | | |
| 24 | Tạo ảnh Gemini Pro | Chọn model `img-gemini-pro`, gõ: "Phong cảnh Hà Nội ban đêm, phong cách sơn dầu" | Ảnh chất lượng cao, chi tiết tốt | | | | |
| 25 | Sửa ảnh qua nhiều lượt | Lượt 1: "Vẽ ngôi nhà", Lượt 2: "Thêm cây xanh xung quanh", Lượt 3: "Đổi sang ban đêm" | Mỗi lượt AI chỉnh sửa dựa trên ảnh trước, chi tiết chính xác | | | | |
| 26 | Tạo ảnh chi tiết phức tạp | Gõ mô tả dài, nhiều chi tiết cụ thể | Ảnh phản ánh đầy đủ hoặc gần đủ mô tả | | | | |
| 27 | Tạo ảnh tiếng Việt | Gõ prompt bằng tiếng Việt hoàn toàn | Hiểu và tạo ảnh đúng mô tả tiếng Việt | | | | |

---

### A3. GỬI FILE & TRUY XUẤT THÔNG TIN

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 28 | Upload PDF | Gửi 1 file PDF (~5 trang) + hỏi nội dung | AI đọc và trả lời chính xác về nội dung file | | | | |
| 29 | Upload Word (.docx) | Gửi 1 file Word + hỏi "Tóm tắt nội dung file" | Tóm tắt đúng, đầy đủ ý chính | | | | |
| 30 | Upload Excel (.xlsx) | Gửi 1 file Excel có bảng số liệu + hỏi "Tổng doanh thu là bao nhiêu?" | Đọc được số liệu, tính toán/trả lời đúng | | | | |
| 31 | Upload CSV | Gửi 1 file CSV + hỏi thông tin | Đọc đúng, trả lời chính xác | | | | |
| 32 | Upload TXT | Gửi 1 file .txt + hỏi nội dung | Đọc và trả lời đúng | | | | |
| 33 | Upload nhiều file cùng lúc | Gửi 3 file khác định dạng (PDF + Excel + TXT) trong 1 lượt | Xử lý được tất cả, trả lời liên quan đến các file | | | | |
| 34 | Upload file lớn | Gửi file PDF ~20-30MB | Upload thành công, AI đọc được (hoặc báo lỗi rõ ràng nếu quá giới hạn) | | | | |
| 35 | Hỏi đáp sâu về file | Sau khi upload, hỏi 3-4 câu liên tiếp về nội dung file | AI nhớ file đã upload, trả lời chính xác từng câu | | | | |
| 36 | Upload HTML | Gửi 1 file .html + hỏi nội dung | Đọc được nội dung text từ HTML | | | | |
| 37 | Trích dẫn nguồn | Hỏi thông tin từ file đã upload | AI trích dẫn tên file, trang/phần nguồn (citation) | | | | |

---

### A4. CHỌN MODEL

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 38 | Danh sách model | Mở dropdown chọn model | Hiển thị đầy đủ tất cả model có sẵn | | | | |
| 39 | GPT-5 | Chọn GPT-5 → hỏi 1 câu | Trả lời thành công, chất lượng cao | | | | |
| 40 | GPT-5 Mini | Chọn GPT-5 Mini → hỏi 1 câu | Trả lời nhanh hơn GPT-5, chất lượng tốt | | | | |
| 41 | GPT-4o | Chọn GPT-4o → hỏi 1 câu | Trả lời thành công | | | | |
| 42 | GPT-4.1 | Chọn GPT-4.1 → hỏi 1 câu | Trả lời thành công | | | | |
| 43 | Gemini 2.5 Pro | Chọn Gemini 2.5 Pro → hỏi 1 câu | Trả lời thành công, tiếng Việt tốt | | | | |
| 44 | Gemini 2.5 Flash | Chọn Gemini 2.5 Flash → hỏi 1 câu | Trả lời nhanh, chất lượng ổn | | | | |
| 45 | Gemini 3 Pro | Chọn Gemini 3 Pro → hỏi 1 câu | Model flagship mới nhất, trả lời tốt | | | | |
| 46 | Chuyển model giữa chừng | Đang chat GPT-5 → đổi sang Gemini → hỏi tiếp | Hội thoại tiếp tục, model mới trả lời đúng | | | | |
| 47 | Model mặc định | Settings → chọn model mặc định | Chat mới tự động dùng model đã chọn | | | | |

---

### A5. KHO KIẾN THỨC (KNOWLEDGE BASE)

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 48 | Tạo Knowledge | Workspace → Knowledge → Create → đặt tên | Collection được tạo thành công | | | | |
| 49 | Upload PDF vào Knowledge | Upload file PDF (~5MB) vào Knowledge | File upload thành công, được index | | | | |
| 50 | Upload Word vào Knowledge | Upload file .docx vào Knowledge | Upload thành công | | | | |
| 51 | Upload Excel vào Knowledge | Upload file .xlsx vào Knowledge | Upload thành công | | | | |
| 52 | Upload CSV vào Knowledge | Upload file .csv vào Knowledge | Upload thành công | | | | |
| 53 | Upload nhiều file | Upload 5+ file khác nhau vào 1 Knowledge | Tất cả upload thành công | | | | |
| 54 | Upload file lớn | Upload file ~30-50MB | Upload thành công (hoặc báo lỗi rõ nếu vượt giới hạn) | | | | |
| 55 | Gọi Knowledge bằng # | Trong chat, gõ `#tên-knowledge` | Hiển thị gợi ý, chọn được Knowledge | | | | |
| 56 | Hỏi đáp từ Knowledge | Gọi #knowledge rồi hỏi về nội dung file đã upload | AI trả lời dựa trên nội dung Knowledge, có trích dẫn | | | | |
| 57 | Xóa file khỏi Knowledge | Xóa 1 file trong Knowledge | File bị xóa, embedding bị xóa theo | | | | |
| 58 | Xóa Knowledge | Xóa cả collection | Collection và toàn bộ file/embedding bị xóa | | | | |

---

### A6. KHÔNG GIAN LÀM VIỆC (WORKSPACE)

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 59 | Tạo Workspace | Tạo Workspace mới | Workspace được tạo thành công | | | | |
| 60 | Chọn Workspace | Chuyển đổi giữa các Workspace | Chuyển đổi mượt, dữ liệu riêng biệt | | | | |
| 61 | Chia sẻ Knowledge | Chia sẻ Knowledge cho user khác | User khác truy cập được Knowledge đã chia sẻ | | | | |
| 62 | Access control | Giới hạn quyền truy cập Knowledge | Chỉ user được phép mới truy cập được | | | | |

---

### A7. GIỌNG NÓI (VOICE)

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 63 | Text-to-Speech | Nhấn icon 🔊 trên response AI | AI đọc nội dung bằng giọng nói tự nhiên | | | | |
| 64 | Speech-to-Text | Nhấn icon 🎤 → nói câu hỏi | Giọng nói được chuyển thành text chính xác | | | | |
| 65 | STT tiếng Việt | Nói bằng tiếng Việt | Nhận dạng tiếng Việt chính xác | | | | |

---

### A8. TÌM KIẾM WEB

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 66 | Web search cơ bản | Hỏi: "Tin tức mới nhất hôm nay về AI" | AI search web, trả lời có nguồn trích dẫn | | | | |
| 67 | Trích dẫn nguồn web | Kiểm tra response có tag nguồn URL | Hiển thị chip/tag website + URL nguồn | | | | |
| 68 | Search tiếng Việt | Hỏi: "Thời tiết Hà Nội hôm nay" | Tìm và trả lời bằng tiếng Việt, có nguồn | | | | |

---

### A9. CÁ NHÂN HÓA & GIAO DIỆN

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 69 | Dark/Light mode | Settings → Theme → chuyển đổi | Giao diện chuyển đổi mượt, không lỗi | | | | |
| 70 | Ngôn ngữ | Settings → Language → chọn Tiếng Việt | Toàn bộ UI chuyển tiếng Việt | | | | |
| 71 | System prompt | Settings → đặt system prompt riêng | AI tuân theo system prompt khi chat | | | | |
| 72 | Responsive mobile | Mở trên điện thoại / thu nhỏ trình duyệt | Giao diện hiển thị tốt, không bị vỡ layout | | | | |

---

## PHẦN B: TÍNH NĂNG QUẢN TRỊ (ADMIN)

---

### B1. QUẢN LÝ NGƯỜI DÙNG

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 73 | Xem danh sách user | Admin Panel → Users | Hiển thị đầy đủ danh sách user, role, trạng thái | | | | |
| 74 | Tạo user mới | Tạo account mới (hoặc đăng ký) | Account được tạo, trạng thái Pending | | | | |
| 75 | Duyệt user | Approve user pending | User chuyển sang Active, đăng nhập được | | | | |
| 76 | Đổi role | Thay đổi role User → Admin | Role thay đổi, quyền thay đổi theo | | | | |
| 77 | Xóa user | Xóa 1 user account | User bị xóa, không đăng nhập được nữa | | | | |
| 78 | Reset password | Reset password cho user | Password mới hoạt động | | | | |

---

### B2. QUẢN LÝ MODEL

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 79 | Bật/tắt model | Admin → Models → Disable 1 model | User không thấy model đã disable | | | | |
| 80 | Cấu hình params | Set temperature, max_tokens cho model | Params áp dụng khi user chat | | | | |
| 81 | Gán Knowledge vào model | Gán Knowledge mặc định cho 1 model | Model tự động sử dụng Knowledge khi chat | | | | |
| 82 | Access control model | Giới hạn model cho user cụ thể | Chỉ user được phép mới thấy model | | | | |

---

### B3. DASHBOARD & GIÁM SÁT

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 83 | Dashboard tổng quan | Truy cập Dashboard middleware | Hiển thị tổng chi phí, số request, top users | | | | |
| 84 | Log requests | Xem log chi tiết từng API request | Hiển thị user, model, tokens, cost, timestamp | | | | |
| 85 | Báo cáo theo user | Lọc chi phí theo user cụ thể | Dữ liệu chính xác theo user được chọn | | | | |
| 86 | Báo cáo theo model | Lọc chi phí theo model cụ thể | Dữ liệu chính xác theo model | | | | |
| 87 | Báo cáo theo thời gian | Lọc theo khoảng thời gian | Dữ liệu đúng trong khoảng thời gian chọn | | | | |

---

### B4. QUOTA & CHI PHÍ

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 88 | Set quota user | Dashboard → set limit_cost_usd cho user | Quota được lưu thành công | | | | |
| 89 | Cảnh báo quota | User chat gần hết quota | Hiển thị cảnh báo cho user | | | | |
| 90 | Chặn khi hết quota | User vượt quota → chat tiếp | Hệ thống từ chối, báo lỗi HTTP 429 | | | | |
| 91 | Sub-key API | Kiểm tra user có sub-key riêng | Mỗi user có API key riêng biệt | | | | |

---

### B5. CẤU HÌNH HỆ THỐNG

| STT | Nhóm tính năng | Câu hỏi / Thao tác test | Kỳ vọng | Câu trả lời thực tế | Kết quả | Đánh giá (1-5) | Ghi chú / Bug |
|-----|----------------|--------------------------|---------|----------------------|---------|-----------------|----------------|
| 92 | WebUI settings | Admin → Settings → General → thay đổi config | Cấu hình được lưu và áp dụng | | | | |
| 93 | Connections | Admin → Settings → Connections | Hiển thị kết nối LLM providers, status OK | | | | |
| 94 | RAG config | Điều chỉnh chunk size, file limit | Thay đổi được áp dụng | | | | |
| 95 | Signup control | Bật/tắt đăng ký mới | Phản ánh đúng: bật → đăng ký được, tắt → không | | | | |

---

## PHẦN C: BẢNG TỔNG HỢP KẾT QUẢ

| Nhóm tính năng | Tổng test case | PASS | FAIL | PARTIAL | SKIP | Tỷ lệ PASS |
|-----------------|---------------|------|------|---------|------|-------------|
| A1. Hỏi đáp (Chat AI) | 21 | | | | | |
| A2. Tạo ảnh AI | 6 | | | | | |
| A3. Gửi file & truy xuất | 10 | | | | | |
| A4. Chọn model | 10 | | | | | |
| A5. Kho kiến thức | 11 | | | | | |
| A6. Workspace | 4 | | | | | |
| A7. Giọng nói | 3 | | | | | |
| A8. Tìm kiếm web | 3 | | | | | |
| A9. Cá nhân hóa & UI | 4 | | | | | |
| B1. Quản lý người dùng | 6 | | | | | |
| B2. Quản lý model | 4 | | | | | |
| B3. Dashboard & giám sát | 5 | | | | | |
| B4. Quota & chi phí | 4 | | | | | |
| B5. Cấu hình hệ thống | 4 | | | | | |
| **TỔNG CỘNG** | **95** | | | | | |

---

## THÔNG TIN NGƯỜI TEST

| Thông tin | Giá trị |
|-----------|---------|
| Họ và tên | |
| Phòng ban | |
| Ngày test | |
| Trình duyệt sử dụng | |
| Thiết bị (PC/Mobile) | |
| Nhận xét chung | |
| Đề xuất cải thiện | |

---

> **Ghi chú**: Form này bao gồm 95 test case, chia thành 14 nhóm tính năng.  
> Các anh/chị vui lòng test từng mục và điền kết quả vào các cột tương ứng.  
> Mọi bug hoặc vấn đề phát hiện xin ghi rõ vào cột "Ghi chú / Bug".
