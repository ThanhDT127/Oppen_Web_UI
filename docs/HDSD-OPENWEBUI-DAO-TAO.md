# 📘 HƯỚNG DẪN SỬ DỤNG OPEN WEBUI — TÀI LIỆU ĐÀO TẠO

> **Phiên bản:** 1.0 | **Ngày tạo:** 31/03/2026  
> **Hệ thống:** Open WebUI Stack (Open WebUI + Middleware + LiteLLM + PostgreSQL)  
> **Đối tượng:** Toàn bộ nhân viên (Người dùng) và Quản trị viên (Admin)

---

## 📋 MỤC LỤC

### PHẦN A — DÀNH CHO NGƯỜI DÙNG

| Chương | Nội dung | Trang |
|--------|----------|-------|
| 1 | [Đăng nhập & Đăng ký](#chương-1-đăng-nhập--đăng-ký) | — |
| 2 | [Tổng quan giao diện](#chương-2-tổng-quan-giao-diện) | — |
| 3 | [Hỏi đáp AI — Chat thông minh](#chương-3-hỏi-đáp-ai--chat-thông-minh) | — |
| 4 | [Chọn Model AI](#chương-4-chọn-model-ai) | — |
| 5 | [Tạo ảnh bằng AI](#chương-5-tạo-ảnh-bằng-ai) | — |
| 6 | [Gửi file & Hỏi đáp tài liệu (RAG)](#chương-6-gửi-file--hỏi-đáp-tài-liệu-rag) | — |
| 7 | [Kho kiến thức (Knowledge Base)](#chương-7-kho-kiến-thức-knowledge-base) | — |
| 8 | [Không gian làm việc (Workspace)](#chương-8-không-gian-làm-việc-workspace) | — |
| 9 | [Xuất file (Excel, PDF, Word)](#chương-9-xuất-file-excel-pdf-word) | — |
| 10 | [Giọng nói — Nghe và Nói](#chương-10-giọng-nói--nghe-và-nói) | — |
| 11 | [Tìm kiếm Web](#chương-11-tìm-kiếm-web) | — |
| 12 | [Quản lý hội thoại](#chương-12-quản-lý-hội-thoại) | — |

### PHẦN B — DÀNH CHO QUẢN TRỊ VIÊN (ADMIN)

| Chương | Nội dung | Trang |
|--------|----------|-------|
| 13 | [Dashboard — Bảng điều khiển](#chương-13-dashboard--bảng-điều-khiển) | — |
| 14 | [Quản lý người dùng](#chương-14-quản-lý-người-dùng) | — |
| 15 | [Quản lý chi phí & Quota](#chương-15-quản-lý-chi-phí--quota) | — |
| 16 | [Cảnh báo tự động](#chương-16-cảnh-báo-tự-động) | — |
| 17 | [Bảo mật & Quản lý Key](#chương-17-bảo-mật--quản-lý-key) | — |
| 18 | [Vận hành hệ thống & FAQ](#chương-18-vận-hành-hệ-thống--faq) | — |

---
---

# PHẦN A — DÀNH CHO NGƯỜI DÙNG

---

## Chương 1. Đăng nhập & Đăng ký

### 1.1. Truy cập hệ thống

Mở trình duyệt web (Chrome, Firefox, Edge đều được) và truy cập địa chỉ:

```
https://openwebui.example.com:51122/
```

Nếu bạn đang ở mạng nội bộ công ty, cũng có thể dùng:

```
https://10.0.0.1:3000/
```

> 💡 **Mẹo:** Lưu trang vào bookmark để truy cập nhanh mỗi ngày.

<!-- 📸 Thêm ảnh: Màn hình đăng nhập Open WebUI -->

### 1.2. Đăng ký tài khoản mới

Nếu bạn chưa có tài khoản:

1. Tại màn hình đăng nhập, nhấn **"Sign up"** (Đăng ký)
2. Điền thông tin:
   - **Họ tên:** Tên hiển thị của bạn (ví dụ: Nguyễn Văn A)
   - **Email:** Email công ty (ví dụ: vana@example.com)
   - **Mật khẩu:** Đặt mật khẩu đủ mạnh (tối thiểu 8 ký tự)
3. Nhấn **"Create Account"**

<!-- 📸 Thêm ảnh: Form đăng ký tài khoản -->

> ⚠️ **Lưu ý:** Sau khi đăng ký, tài khoản của bạn ở trạng thái **"Pending"** (chờ duyệt). Admin sẽ duyệt tài khoản trong vòng 1 ngày làm việc. Bạn sẽ nhận được thông báo khi tài khoản được kích hoạt.

### 1.3. Đăng nhập

1. Nhập **Email** và **Mật khẩu** đã đăng ký
2. Nhấn **"Sign in"**
3. Hệ thống chuyển bạn vào giao diện chat

<!-- 📸 Thêm ảnh: Nhập thông tin đăng nhập -->

### 1.4. Đổi mật khẩu

1. Nhấn vào **tên của bạn** (góc dưới bên trái)
2. Chọn **"Settings"** (Cài đặt)
3. Vào tab **"Account"**
4. Tìm mục **"Change Password"**, nhập mật khẩu cũ và mật khẩu mới
5. Nhấn **"Save"**

<!-- 📸 Thêm ảnh: Màn hình đổi mật khẩu trong Settings > Account -->

---

## Chương 2. Tổng quan giao diện

Sau khi đăng nhập thành công, bạn sẽ thấy giao diện chính gồm các khu vực sau:

<!-- 📸 Thêm ảnh: Tổng quan giao diện chính với đánh số từng khu vực -->

### 2.1. Thanh bên trái (Sidebar)

Đây là nơi bạn quản lý tất cả hội thoại:

- **🔍 Thanh tìm kiếm:** Tìm nhanh hội thoại cũ theo từ khóa
- **✏️ Nút "New Chat":** Bắt đầu cuộc trò chuyện mới
- **📁 Folders:** Các thư mục bạn tạo để sắp xếp hội thoại
- **💬 Danh sách hội thoại:** Toàn bộ hội thoại cũ, sắp xếp theo thời gian

<!-- 📸 Thêm ảnh: Sidebar với các thành phần được chú thích -->

### 2.2. Khu vực chat (giữa màn hình)

- **Phía trên:** Dòng chọn Model AI (ví dụ: "mm-gemini-2.5-flash")
- **Giữa:** Nội dung hội thoại — tin nhắn của bạn và phản hồi từ AI
- **Phía dưới:** Ô nhập tin nhắn + các nút gửi file, ghi âm

<!-- 📸 Thêm ảnh: Khu vực chat chính với khung nhập tin nhắn -->

### 2.3. Thanh công cụ dưới mỗi tin nhắn AI

Mỗi tin nhắn AI trả về đều có một thanh công cụ nhỏ phía dưới:

| Icon | Chức năng |
|------|-----------|
| 📋 | **Copy** — Sao chép nội dung tin nhắn |
| 👍 👎 | **Đánh giá** — Đánh giá câu trả lời tốt/chưa tốt |
| 🔊 | **Đọc to** — AI đọc nội dung bằng giọng nói |
| 🔄 | **Regenerate** — Yêu cầu AI trả lời lại |
| ⚡ | **Actions** — Các công cụ mở rộng (xuất file, v.v.) |

<!-- 📸 Thêm ảnh: Thanh công cụ bên dưới tin nhắn AI, chú thích từng icon -->

### 2.4. Menu cá nhân (góc dưới bên trái)

Nhấn vào **tên hoặc avatar** của bạn để mở menu:

- **Settings:** Cài đặt cá nhân (ngôn ngữ, giao diện, model mặc định)
- **Archived Chats:** Xem các hội thoại đã lưu trữ
- **Sign Out:** Đăng xuất

<!-- 📸 Thêm ảnh: Menu cá nhân khi nhấn vào avatar -->

### 2.5. Chuyển giao diện Sáng/Tối

1. Vào **Settings** → **General**
2. Mục **Theme**, chọn:
   - ☀️ **Light** — Giao diện sáng
   - 🌙 **Dark** — Giao diện tối (dễ nhìn khi làm việc lâu)
   - 🖥️ **System** — Tự động theo cài đặt máy tính

<!-- 📸 Thêm ảnh: Tùy chọn theme trong Settings -->

### 2.6. Đổi ngôn ngữ

1. Vào **Settings** → **General**
2. Mục **Language**, chọn **"Tiếng Việt"** hoặc **"English"**
3. Giao diện sẽ tự động chuyển ngôn ngữ

<!-- 📸 Thêm ảnh: Dropdown chọn ngôn ngữ -->

---

## Chương 3. Hỏi đáp AI — Chat thông minh

Đây là chức năng chính và được sử dụng nhiều nhất. Bạn có thể hỏi AI bất cứ điều gì: soạn văn bản, dịch thuật, phân tích dữ liệu, viết code, brainstorm ý tưởng...

### 3.1. Bắt đầu cuộc trò chuyện mới

1. Nhấn nút **"New Chat"** (✏️) ở góc trên bên trái
2. Chọn model AI phù hợp (xem Chương 4 để biết nên chọn model nào)
3. Gõ câu hỏi vào ô chat phía dưới
4. Nhấn **Enter** hoặc nhấn nút **gửi** (▶️)

<!-- 📸 Thêm ảnh: Bước tạo chat mới và gõ câu hỏi đầu tiên -->

AI sẽ trả lời ngay lập tức. Câu trả lời hiện dần từng chữ (streaming) để bạn bắt đầu đọc ngay mà không cần đợi hết.

### 3.2. Gõ tiếp để hỏi nhiều lượt

Bạn có thể tiếp tục hỏi trong cùng một cuộc trò chuyện. AI sẽ **nhớ toàn bộ nội dung đã trao đổi** và trả lời dựa trên ngữ cảnh trước đó.

**Ví dụ:**

```
Bạn: Tóm tắt 5 điểm chính của quản trị rủi ro
AI:  (trả lời 5 điểm)

Bạn: Giải thích chi tiết điểm số 3
AI:  (hiểu điểm 3 là điểm nào và giải thích thêm)

Bạn: Viết thành email gửi sếp
AI:  (soạn email dựa trên nội dung đã thảo luận)
```

<!-- 📸 Thêm ảnh: Cuộc trò chuyện nhiều lượt thể hiện ngữ cảnh liên tục -->

### 3.3. Một số mẹo viết prompt hay

Để AI trả lời chất lượng hơn, bạn nên:

| Mẹo | Ví dụ tốt | Ví dụ chưa tốt |
|-----|-----------|-----------------|
| **Nêu rõ vai trò** | "Bạn là chuyên gia marketing, hãy..." | "Viết cho tôi..." |
| **Yêu cầu cụ thể** | "Liệt kê 5 ý, mỗi ý 2 câu" | "Nói về..." |
| **Cho ví dụ** | "Viết giống mẫu sau: [mẫu]" | "Viết hay lên" |
| **Chỉ định format** | "Trả lời dạng bảng, có 3 cột" | "Cho tôi thông tin" |
| **Giới hạn độ dài** | "Trả lời trong 200 từ" | (không giới hạn → quá dài) |

### 3.4. AI hiển thị nội dung đẹp

AI có thể trả lời với nhiều định dạng phong phú:

- **Bảng biểu** — so sánh, thống kê
- **Code** — có highlight màu theo ngôn ngữ lập trình
- **Danh sách** — bullet points, đánh số
- **Markdown** — in đậm, in nghiêng, tiêu đề
- **Công thức toán** — LaTeX

<!-- 📸 Thêm ảnh: Tin nhắn AI có bảng, code block, danh sách -->

### 3.5. Đổi model giữa chừng

Bạn hoàn toàn có thể đổi sang model khác giữa cuộc trò chuyện:

1. Nhấn vào **tên model** ở phía trên khung chat
2. Chọn model mới từ danh sách
3. Tiếp tục chat — model mới sẽ đọc lại toàn bộ lịch sử để hiểu ngữ cảnh

<!-- 📸 Thêm ảnh: Dropdown đổi model giữa cuộc chat -->

> 💡 **Khi nào nên đổi model?** Khi bạn cảm thấy câu trả lời chưa đủ sâu, thử chuyển sang model mạnh hơn (ví dụ: từ `mm-gemini-2.5-flash` sang `mm-gpt-5`).

### 3.6. Gửi ảnh kèm câu hỏi (Multimodal)

Một số model hỗ trợ đọc ảnh. Bạn có thể gửi ảnh chụp màn hình, biểu đồ, bảng số liệu... để AI phân tích.

1. Nhấn nút **📎 (Attach)** bên cạnh ô chat
2. Chọn ảnh từ máy tính
3. Gõ câu hỏi về ảnh, ví dụ: *"Phân tích biểu đồ này"*
4. Nhấn gửi

<!-- 📸 Thêm ảnh: Gửi ảnh kèm câu hỏi cho AI phân tích -->

> ⚠️ **Lưu ý:** Chỉ các model có prefix `mm-` mới hỗ trợ đọc ảnh. Xem danh sách chi tiết ở Chương 4.

### 3.7. Yêu cầu AI trả lời lại

Nếu câu trả lời chưa ưng ý:

- Nhấn nút **🔄 Regenerate** — AI sẽ trả lời lại (có thể ra kết quả khác)
- Hoặc gõ thêm yêu cầu: *"Viết lại ngắn gọn hơn"*, *"Thêm ví dụ cụ thể"*

<!-- 📸 Thêm ảnh: Nút Regenerate dưới tin nhắn AI -->

---

## Chương 4. Chọn Model AI

Hệ thống cung cấp nhiều model AI từ các nhà cung cấp hàng đầu (OpenAI, Google). Mỗi model có thế mạnh riêng. Chọn đúng model giúp bạn có câu trả lời tốt nhất và tiết kiệm chi phí.

### 4.1. Quy ước đặt tên Model

Tên model luôn bắt đầu bằng một **prefix** cho biết loại chức năng:

| Prefix | Ý nghĩa | Ví dụ |
|--------|----------|-------|
| `mm-` | **Multimodal** — Chat text + đọc ảnh | `mm-gpt-5`, `mm-gemini-2.5-flash` |
| `img-` | **Image** — Tạo ảnh từ mô tả | `img-dalle-3`, `img-gemini-flash` |
| `tts-` | **Text-to-Speech** — Đọc text thành giọng nói | `tts-gpt-4o-mini` |
| `stt-` | **Speech-to-Text** — Chuyển giọng nói thành text | `stt-gpt-4o` |

<!-- 📸 Thêm ảnh: Dropdown chọn model với danh sách hiện ra -->

### 4.2. Bảng so sánh Model Chat

Đây là các model bạn dùng hàng ngày để hỏi đáp:

| Model | Nhà cung cấp | Tốc độ | Chất lượng | Chi phí | Dùng khi nào? |
|-------|-------------|--------|------------|---------|---------------|
| `mm-gemini-2.5-flash` | Google | ⚡⚡⚡ | ⭐⭐⭐⭐ | 💲 | **Khuyến nghị mặc định** — nhanh, chất lượng tốt, tiết kiệm |
| `mm-gpt-5-mini` | OpenAI | ⚡⚡⚡ | ⭐⭐⭐⭐ | 💲💲 | Tác vụ thường ngày, soạn email, dịch |
| `mm-gpt-5` | OpenAI | ⚡⚡ | ⭐⭐⭐⭐⭐ | 💲💲💲 | Phân tích phức tạp, suy luận logic |
| `mm-gemini-2.5-pro` | Google | ⚡⚡ | ⭐⭐⭐⭐⭐ | 💲💲💲 | Reasoning mạnh, tiếng Việt tốt |
| `mm-gemini-3-pro` | Google | ⚡⚡ | ⭐⭐⭐⭐⭐ | 💲💲💲 | Model mới nhất, flagship |
| `mm-gpt-5-nano` | OpenAI | ⚡⚡⚡ | ⭐⭐⭐ | 💲 | Nhanh nhất, câu hỏi đơn giản |
| `mm-gpt-4.1` | OpenAI | ⚡⚡ | ⭐⭐⭐⭐ | 💲💲 | Tài liệu dài (1M context) |
| `mm-gpt-4o` | OpenAI | ⚡⚡⚡ | ⭐⭐⭐⭐ | 💲💲 | Multimodal tốt (ảnh + audio) |

### 4.3. Gợi ý chọn model theo tình huống

| Bạn muốn... | Model nên dùng |
|-------------|----------------|
| Hỏi nhanh, soạn email, dịch | `mm-gemini-2.5-flash` |
| Phân tích hợp đồng, báo cáo dài | `mm-gpt-4.1` (1M context) |
| Suy luận logic, toán, code | `mm-gpt-5` hoặc `mm-gemini-2.5-pro` |
| Đọc và phân tích ảnh, biểu đồ | `mm-gpt-4o` |
| Chat nhẹ, brainstorm nhanh | `mm-gpt-5-nano` |

### 4.4. Đặt model mặc định

Nếu bạn hay dùng 1 model nhất định, hãy đặt nó làm mặc định:

1. Vào **Settings** (nhấn vào tên bạn ở góc dưới trái)
2. Chọn tab **General**
3. Mục **"Default Model"** — chọn model bạn thích
4. Nhấn **Save**

Từ giờ mỗi khi tạo chat mới, model này sẽ được chọn sẵn.

<!-- 📸 Thêm ảnh: Settings > General > Default Model -->

---

## Chương 5. Tạo ảnh bằng AI

Bạn có thể nhờ AI tạo ảnh minh họa, banner, poster, mockup... chỉ bằng cách mô tả bằng lời.

### 5.1. Các model tạo ảnh hiện có

| Model | Nhà cung cấp | Chất lượng | Ghi chú |
|-------|-------------|------------|---------|
| `img-gemini-flash` | Google | ⭐⭐⭐⭐ | ✅ **Khuyến nghị** — nhanh, chất lượng tốt |
| `img-gemini-pro` | Google | ⭐⭐⭐⭐⭐ | Chất lượng cao, lên đến 4K |
| `img-dalle-3` | OpenAI | ⭐⭐⭐⭐⭐ | Chất lượng cao, 1024×1024 |

### 5.2. Cách tạo ảnh

1. **Chọn model ảnh:** Nhấn vào dropdown model ở đầu trang, chọn model bắt đầu bằng `img-` (ví dụ: `img-gemini-flash`)
2. **Mô tả ảnh muốn tạo:** Gõ mô tả chi tiết vào ô chat
3. Nhấn **Enter** và đợi vài giây

**Ví dụ prompt tạo ảnh:**

```
Một poster quảng cáo bóng đèn LED tiết kiệm năng lượng, 
phong cách hiện đại, nền xanh dương, có đèn đang phát sáng, 
text "Save Energy" ở góc trên
```

<!-- 📸 Thêm ảnh: Kết quả tạo ảnh từ AI - ảnh được hiển thị trong chat -->

### 5.3. Chỉnh sửa ảnh qua nhiều lượt

Điểm mạnh của hệ thống là bạn có thể **trao đổi nhiều lượt** để tinh chỉnh ảnh:

```
Bạn: Tạo logo cho dự án "Green Office", phong cách minimalist
AI:  (tạo ảnh lần 1)

Bạn: Đẹp rồi, nhưng đổi màu nền sang xanh lá đậm hơn
AI:  (tạo ảnh cập nhật)

Bạn: Thêm icon chiếc lá nhỏ bên cạnh chữ
AI:  (tạo ảnh cuối cùng)
```

<!-- 📸 Thêm ảnh: Ví dụ trao đổi nhiều lượt chỉnh sửa ảnh -->

### 5.4. Mẹo mô tả ảnh hiệu quả

| Nên | Không nên |
|-----|-----------|
| Mô tả chi tiết: chủ thể, phong cách, màu sắc, bố cục | Chỉ viết mơ hồ: "vẽ đẹp đẹp" |
| Nêu phong cách: "realistic", "watercolor", "3D render" | Không nêu phong cách |
| Chỉ rõ kích thước/tỷ lệ nếu cần | Bỏ qua yêu cầu về kích thước |
| Viết bằng tiếng Anh thường cho kết quả tốt hơn | — |

### 5.5. Tải ảnh về máy

Khi AI tạo ảnh xong, ảnh sẽ hiện trực tiếp trong chat. Để tải về:

1. **Nhấn chuột phải** vào ảnh
2. Chọn **"Save image as..."** (Lưu ảnh)
3. Chọn thư mục và nhấn Save

<!-- 📸 Thêm ảnh: Chuột phải vào ảnh AI tạo > Save image -->

---

## Chương 6. Gửi file & Hỏi đáp tài liệu (RAG)

Một trong những tính năng mạnh nhất của hệ thống: bạn có thể **gửi file tài liệu** cho AI và **hỏi bất cứ điều gì** về nội dung trong file đó. AI sẽ đọc, hiểu và trả lời chính xác dựa trên tài liệu của bạn.

### 6.1. Các loại file được hỗ trợ

| Loại file | Định dạng | Ghi chú |
|-----------|-----------|---------|
| 📄 PDF | `.pdf` | Hỗ trợ OCR (đọc ảnh trong PDF) |
| 📝 Word | `.docx` | Đọc toàn bộ nội dung text |
| 📊 Excel | `.xlsx` | Đọc dữ liệu trong các sheet |
| 📋 Text | `.txt`, `.csv`, `.md` | Đọc trực tiếp |
| 🌐 HTML | `.html` | Trích xuất nội dung |

> **Giới hạn:** Mỗi file tối đa **50 MB**. Có thể gửi nhiều file cùng lúc.

### 6.2. Cách gửi file trong chat (nhanh)

Đây là cách đơn giản nhất — gửi file trực tiếp vào cuộc chat:

1. Nhấn nút **📎 (Attach file)** cạnh ô nhập tin nhắn
2. Chọn file từ máy tính (có thể chọn **nhiều file** cùng lúc bằng cách giữ Ctrl + click)
3. Đợi vài giây để hệ thống xử lý file (hiện thanh progress)
4. Gõ câu hỏi và nhấn Enter

**Hoặc đơn giản hơn:** Kéo thả file từ máy tính vào cửa sổ chat.

<!-- 📸 Thêm ảnh: Kéo thả file vào cửa sổ chat, hiện preview file -->

### 6.3. Hỏi đáp về nội dung file

Sau khi gửi file, bạn hỏi bất cứ gì:

```
Bạn: [đính kèm: bao-cao-tai-chinh-Q1.xlsx]
     Tóm tắt doanh thu theo tháng trong file này

AI:  Dựa trên file báo cáo tài chính Q1, doanh thu theo từng tháng:
     - Tháng 1: 2.5 tỷ VNĐ (+12% so với cùng kỳ)
     - Tháng 2: 1.8 tỷ VNĐ (-5% do nghỉ Tết)
     - Tháng 3: 3.1 tỷ VNĐ (+20%)
     [Nguồn: Sheet "Revenue", cột B-C]
```

```
Bạn: [đính kèm: hop-dong-nha-cung-cap.pdf]
     Liệt kê các điều khoản thanh toán trong hợp đồng này

AI:  Theo hợp đồng, các điều khoản thanh toán bao gồm:
     1. Đặt cọc 30% khi ký kết (Điều 5.1)
     2. Thanh toán 50% khi giao hàng (Điều 5.2)
     ...
```

<!-- 📸 Thêm ảnh: Ví dụ hỏi đáp dựa trên file PDF đã gửi -->

### 6.4. Gửi nhiều file cùng lúc

Bạn có thể gửi **tối đa 20 file** trong một lần:

1. Nhấn 📎 → giữ **Ctrl** + click chọn nhiều file
2. Tất cả file sẽ hiện dưới dạng chip bên dưới ô chat
3. Gõ câu hỏi tổng hợp: *"So sánh nội dung 2 file này"*

<!-- 📸 Thêm ảnh: Nhiều file đang được đính kèm, hiện dạng chips -->

### 6.5. Truy xuất bằng ký hiệu # (nâng cao)

Ngoài cách gửi file trực tiếp, bạn còn có thể gọi tên file hoặc Knowledge Base bằng ký hiệu `#`:

```
# Truy xuất file đã upload trước đó
#bao-cao-Q1.pdf Tóm tắt phần kết luận

# Truy xuất Knowledge Base (kho kiến thức)
#QuyDinhCongTy Quy định nghỉ phép là gì?

# Truy xuất nội dung từ URL
#https://example.com Tóm tắt trang này
```

Khi gõ `#`, hệ thống sẽ hiện gợi ý các file và Knowledge Base có sẵn.

<!-- 📸 Thêm ảnh: Gõ # trong chat, hiện dropdown gợi ý file/KB -->

### 6.6. AI trích dẫn nguồn (Citations)

Khi trả lời dựa trên tài liệu, AI sẽ **trích dẫn nguồn** — bạn biết chính xác thông tin lấy từ đâu:

- Tên file gốc
- Trang hoặc đoạn liên quan
- Chip nguồn có thể nhấn vào để xem chi tiết

<!-- 📸 Thêm ảnh: Câu trả lời AI có citations (chip nguồn bên dưới) -->

> 💡 **Lưu ý:** File gửi trực tiếp trong chat chỉ tồn tại **trong cuộc trò chuyện đó**. Nếu muốn lưu lâu dài để dùng cho nhiều cuộc chat, hãy tải lên **Kho kiến thức** (xem Chương 7).

---

## Chương 7. Kho kiến thức (Knowledge Base)

Knowledge Base là nơi bạn tải lên tài liệu để AI có thể truy xuất **bất cứ lúc nào**, trong **bất kỳ cuộc chat nào**. Khác với gửi file trực tiếp (chỉ dùng 1 lần), Knowledge Base lưu trữ lâu dài và có thể chia sẻ cho đồng nghiệp.

### 7.1. Tạo Knowledge Base mới

1. Nhấn vào **Workspace** (thanh bên trái, phía trên)
2. Chọn tab **"Knowledge"**
3. Nhấn nút **"+ Create"** hoặc **"Create Knowledge"**
4. Điền thông tin:
   - **Name:** Đặt tên ngắn gọn (ví dụ: "Quy định công ty 2026")
   - **Description:** Mô tả nội dung (ví dụ: "Tổng hợp nội quy, quy chế, quy trình")
5. Nhấn **"Create"**

<!-- 📸 Thêm ảnh: Màn hình tạo Knowledge mới -->

### 7.2. Tải file lên Knowledge Base

Sau khi tạo Knowledge Base:

1. Nhấn vào Knowledge Base vừa tạo
2. Nhấn **"Upload"** hoặc **kéo thả file** vào khu vực upload
3. Chọn một hoặc nhiều file (PDF, Word, Excel, TXT, CSV, HTML)
4. Đợi hệ thống xử lý — thanh progress hiện từng file

<!-- 📸 Thêm ảnh: Kéo thả nhiều file vào Knowledge Base, thanh progress -->

> **Dung lượng:** Hệ thống hỗ trợ file lên đến **50 MB/file**. Không giới hạn số lượng file trong 1 Knowledge Base (chỉ giới hạn bởi dung lượng server).

### 7.3. Sử dụng Knowledge Base trong chat

Có **2 cách** để dùng Knowledge Base khi chat:

#### Cách 1: Gọi bằng dấu # (nhanh)

Gõ `#` trong ô chat, hệ thống sẽ hiện danh sách Knowledge Base cho bạn chọn:

```
#QuyDinhCongTy Quy trình xin nghỉ phép như thế nào?
```

<!-- 📸 Thêm ảnh: Gõ # để gọi Knowledge Base -->

#### Cách 2: Gán Knowledge Base vào Model (tự động)

Cách này giúp AI **luôn tự động** dùng Knowledge Base mà không cần gõ `#`:

1. Vào **Workspace** → **Models** → nhấn **"+"** tạo model mới
2. Đặt tên (ví dụ: "Trợ lý HR")
3. Chọn **Base Model**: `mm-gemini-2.5-flash`
4. Ở mục **Knowledge**: chọn Knowledge Base mong muốn
5. Nhấn **Save**

Khi chat với model "Trợ lý HR" này, AI sẽ tự động tìm thông tin trong Knowledge Base đã gán.

<!-- 📸 Thêm ảnh: Tạo model mới và gán Knowledge Base -->

### 7.4. Quản lý Knowledge Base

| Thao tác | Cách làm |
|----------|----------|
| Xem danh sách file | Nhấn vào tên Knowledge Base |
| Xóa 1 file | Nhấn icon 🗑️ bên cạnh file |
| Xóa cả Knowledge Base | Nhấn "Delete" khi xem chi tiết KB |
| Chia sẻ cho đồng nghiệp | Cấu hình Access Control (xem mục 7.5) |

<!-- 📸 Thêm ảnh: Danh sách file trong Knowledge Base, các nút thao tác -->

### 7.5. Phân quyền truy cập Knowledge Base

Admin hoặc người tạo Knowledge Base có thể quy định ai được sử dụng:

1. Mở Knowledge Base → nhấn **Settings** (⚙️)
2. Mục **Access Control** — chọn:
   - **Public:** Tất cả mọi người đều dùng được
   - **Private:** Chỉ người tạo dùng được
   - **Shared:** Chỉ định user/nhóm cụ thể

<!-- 📸 Thêm ảnh: Cài đặt Access Control cho Knowledge Base -->

> 🔒 **Bảo mật:** Tài liệu trong Knowledge Base được xử lý 100% trên server nội bộ. Nội dung **không gửi ra bên ngoài** — chỉ có câu hỏi và trích đoạn liên quan mới được gửi đến AI để trả lời.

---

## Chương 8. Không gian làm việc (Workspace)

Workspace là khu vực quản lý các tài nguyên nâng cao: Models tùy chỉnh, Knowledge Base, Prompts, và Tools.

### 8.1. Truy cập Workspace

Nhấn vào **"Workspace"** ở thanh menu phía trên cùng (hoặc sidebar).

<!-- 📸 Thêm ảnh: Nút Workspace trên thanh menu -->

### 8.2. Các tab trong Workspace

| Tab | Chức năng |
|-----|-----------|
| **Models** | Tạo model tùy chỉnh (gán Knowledge, system prompt) |
| **Knowledge** | Quản lý Kho kiến thức (đã nói ở Chương 7) |
| **Prompts** | Lưu trữ các prompt hay dùng để tái sử dụng |
| **Tools** | Các công cụ mở rộng (Admin quản lý) |

<!-- 📸 Thêm ảnh: Giao diện Workspace với 4 tab -->

### 8.3. Tạo Model tùy chỉnh

Bạn có thể tạo "phiên bản model riêng" với các cài đặt đặc biệt:

1. Vào **Workspace** → **Models** → nhấn **"+"**
2. Cấu hình:
   - **Name:** Tên hiển thị (ví dụ: "Trợ lý Kế toán")
   - **Base Model:** Chọn model nền (ví dụ: `mm-gemini-2.5-flash`)
   - **System Prompt:** Viết hướng dẫn cho AI
     ```
     Bạn là trợ lý kế toán, chuyên gia về chuẩn mực kế toán Việt Nam.
     Luôn trả lời bằng tiếng Việt, có trích dẫn điều khoản luật nếu liên quan.
     ```
   - **Knowledge:** Gán Knowledge Base liên quan
3. Nhấn **Save**

<!-- 📸 Thêm ảnh: Form tạo Model tùy chỉnh -->

### 8.4. Lưu Prompt (Saved Prompts)

Nếu bạn hay dùng một prompt dài, lưu lại để gọi nhanh:

1. Vào **Workspace** → **Prompts** → nhấn **"+"**
2. Điền:
   - **Title:** Tên ngắn (ví dụ: "Tóm tắt email")
   - **Command:** Từ khóa gọi nhanh (ví dụ: `/tomtat`)
   - **Content:** Nội dung prompt đầy đủ
3. Nhấn **Save**

Khi chat, gõ `/tomtat` là prompt tự động điền vào ô chat.

<!-- 📸 Thêm ảnh: Tạo Saved Prompt và gõ lệnh / để gọi nhanh -->

### 8.5. Chia sẻ Workspace

- **Models tùy chỉnh** có thể chia sẻ cho đồng nghiệp bằng cách đặt Access Control thành Public hoặc Shared
- **Knowledge Base** cũng chia sẻ tương tự (đã nói ở Chương 7)
- Người được chia sẻ sẽ thấy model/KB xuất hiện trong danh sách của họ

<!-- 📸 Thêm ảnh: Cài đặt chia sẻ model cho nhóm -->

---

## Chương 9. Xuất file (Excel, PDF, Word)

Sau khi AI tạo nội dung (bảng biểu, báo cáo, phân tích...), bạn có thể xuất thành file để lưu trữ hoặc gửi cho đồng nghiệp.

### 9.1. Cách xuất file

1. Trong cuộc chat, tìm tin nhắn AI có nội dung bạn muốn xuất
2. Nhấn nút **⚡ Actions** (bên dưới tin nhắn AI)
3. Chọn **"Xuất File"**
4. Chọn định dạng:
   - **1 = Excel (.xlsx)** — cho bảng biểu, số liệu
   - **2 = PDF** — cho báo cáo, hội thoại
   - **3 = Word (.docx)** — cho tài liệu, văn bản
5. File sẽ **tự động tải xuống** máy tính

<!-- 📸 Thêm ảnh: Nút Actions > Xuất File > Chọn định dạng -->

### 9.2. Xuất Excel

Đặc biệt hữu ích khi AI trả lời có bảng biểu:

- ✅ Tự động nhận dạng: số, ngày tháng, phần trăm, tiền tệ
- ✅ Format đúng: VNĐ, $, €, dấu phẩy hàng nghìn
- ✅ Có filter trên header
- ✅ Cột tự co giãn theo nội dung

<!-- 📸 Thêm ảnh: File Excel đã xuất với format đẹp -->

### 9.3. Xuất PDF

- ✅ Hỗ trợ tiếng Việt đầy đủ (font DejaVu)
- ✅ Giữ nguyên format: bảng, danh sách, code
- ✅ Phù hợp để lưu trữ hoặc in ra

<!-- 📸 Thêm ảnh: File PDF đã xuất -->

### 9.4. Xuất Word

- ✅ Xuất toàn bộ nội dung hội thoại
- ✅ Có thể chỉnh sửa tiếp trong Word
- ✅ Giữ format cơ bản

<!-- 📸 Thêm ảnh: File Word đã xuất -->

---

## Chương 10. Giọng nói — Nghe và Nói

### 10.1. Nghe AI đọc (Text-to-Speech)

Bạn có thể yêu cầu AI **đọc to** câu trả lời:

1. Tìm tin nhắn AI bạn muốn nghe
2. Nhấn nút **🔊 (Speaker)** bên dưới tin nhắn
3. AI sẽ đọc bằng giọng nói tự nhiên

<!-- 📸 Thêm ảnh: Nút speaker dưới tin nhắn AI -->

> Giọng đọc được tạo bởi model `tts-gpt-4o-mini` — giọng tự nhiên, rõ ràng.

### 10.2. Nhập liệu bằng giọng nói (Speech-to-Text)

Thay vì gõ phím, bạn có thể **nói** để nhập câu hỏi:

1. Nhấn nút **🎤 (Microphone)** cạnh ô chat
2. Nói câu hỏi của bạn
3. Hệ thống chuyển giọng nói thành text và hiện trong ô chat
4. Kiểm tra lại rồi nhấn **Enter** để gửi

<!-- 📸 Thêm ảnh: Nút microphone và text được chuyển từ giọng nói -->

> 💡 **Mẹo:** Nói rõ ràng, tốc độ vừa phải sẽ cho kết quả chính xác nhất. Hệ thống nhận dạng tốt cả tiếng Việt lẫn tiếng Anh.

---

## Chương 11. Tìm kiếm Web

AI có thể **tìm kiếm thông tin trên Internet** để trả lời các câu hỏi cần dữ liệu mới nhất (tin tức, giá cả, thời tiết...).

### 11.1. Khi nào AI tự tìm kiếm web?

AI sẽ **tự động** quyết định tìm kiếm web khi nhận ra câu hỏi cần thông tin mới. Bạn không cần làm gì thêm.

**Ví dụ:**

```
Bạn: Giá vàng hôm nay bao nhiêu?
AI:  🔍 Đang tìm kiếm... (Retrieved 5 sources)
     Theo SJC, giá vàng hôm nay 31/03/2026:
     - Mua vào: 130.5 triệu/lượng
     - Bán ra: 132.0 triệu/lượng
     [Nguồn: sjc.com.vn, vnexpress.net]
```

<!-- 📸 Thêm ảnh: AI tìm kiếm web và trả lời kèm nguồn trích dẫn -->

### 11.2. Nguồn tìm kiếm

Hệ thống sử dụng **SearXNG** — công cụ tìm kiếm tự host, tổng hợp kết quả từ:

- 🔍 DuckDuckGo
- 🔍 Brave
- 🔍 Bing

Kết quả kèm theo **trích dẫn nguồn** (chip hiện URL gốc) để bạn có thể kiểm chứng thông tin.

<!-- 📸 Thêm ảnh: Chips trích dẫn nguồn từ web search -->

### 11.3. Chi phí

Tìm kiếm web **miễn phí hoàn toàn** (SearXNG tự host trên server). Bạn chỉ trả chi phí token cho phần AI xử lý kết quả tìm được.

---

## Chương 12. Quản lý hội thoại

### 12.1. Tìm hội thoại cũ

Nhập từ khóa vào **ô tìm kiếm** ở đầu sidebar. Hệ thống tìm theo tiêu đề hội thoại.

<!-- 📸 Thêm ảnh: Thanh search ở sidebar -->

### 12.2. Sắp xếp vào Folder

Tạo folder để tổ chức hội thoại theo chủ đề:

1. Nhấn chuột phải vào hội thoại ở sidebar
2. Chọn **"Move to Folder"**
3. Chọn folder có sẵn hoặc tạo folder mới

<!-- 📸 Thêm ảnh: Menu chuột phải > Move to Folder -->

### 12.3. Ghim hội thoại (Pin)

Ghim những hội thoại quan trọng lên đầu danh sách:

1. Nhấn chuột phải vào hội thoại
2. Chọn **"Pin"**
3. Hội thoại được ghim sẽ hiện ở phía trên cùng sidebar

<!-- 📸 Thêm ảnh: Hội thoại đã pin hiển thị ở trên cùng -->

### 12.4. Lưu trữ (Archive)

Lưu trữ hội thoại không cần nữa nhưng chưa muốn xóa:

1. Nhấn chuột phải → **"Archive"**
2. Để xem lại: vào menu cá nhân → **"Archived Chats"**

<!-- 📸 Thêm ảnh: Archived Chats -->

### 12.5. Gắn thẻ (Tags)

Gắn tag để phân loại hội thoại:

1. Mở hội thoại → nhấn icon **🏷️ (Tag)**
2. Gõ tên tag (ví dụ: "dự án A", "marketing")
3. Nhấn Enter

<!-- 📸 Thêm ảnh: Gắn tag cho hội thoại -->

### 12.6. Chia sẻ hội thoại

Bạn muốn gửi cuộc trò chuyện cho đồng nghiệp xem:

1. Mở hội thoại muốn chia sẻ
2. Nhấn nút **Share** (🔗) ở góc trên
3. Hệ thống tạo **link chia sẻ** — copy và gửi cho đồng nghiệp
4. Người nhận mở link là xem được nội dung (không cần đăng nhập)

<!-- 📸 Thêm ảnh: Nút Share và link chia sẻ được tạo -->

### 12.7. Xóa hội thoại

1. Nhấn chuột phải vào hội thoại → **"Delete"**
2. Xác nhận xóa

> ⚠️ **Xóa là vĩnh viễn** — không thể khôi phục. Hãy cân nhắc Archive nếu chưa chắc.

<!-- 📸 Thêm ảnh: Xác nhận xóa hội thoại -->

---
---

# PHẦN B — DÀNH CHO QUẢN TRỊ VIÊN (ADMIN)

> 📌 Phần này dành cho người có quyền **Admin**. Nếu bạn là người dùng thông thường, các chương ở Phần A là đủ.

---

## Chương 13. Dashboard — Bảng điều khiển

Dashboard là "trung tâm chỉ huy" giúp Admin giám sát toàn bộ hoạt động AI trong tổ chức: ai đang dùng, tốn bao nhiêu, model nào phổ biến...

### 13.1. Truy cập Dashboard

Mở trình duyệt và vào:

```
https://openwebui.example.com:51122/dashboard
```

Hệ thống yêu cầu nhập **Admin Key** (mật khẩu quản trị). Nhập key và nhấn **"Access Dashboard"**.

<!-- 📸 Thêm ảnh: Màn hình đăng nhập Dashboard với ô nhập Admin Key -->

> 🔐 **Bảo mật:** Phiên đăng nhập Dashboard có hiệu lực **4 giờ**. Sau đó bạn cần đăng nhập lại.

### 13.2. Tổng quan giao diện Dashboard

Dashboard gồm các khu vực chính:

<!-- 📸 Thêm ảnh: Tổng quan Dashboard với đánh số từng khu vực -->

### 13.3. 7 thẻ chỉ số chính (Metrics Cards)

Phía trên cùng hiển thị 7 thẻ thống kê quan trọng:

| Thẻ | Ý nghĩa | Khi nào cần chú ý? |
|-----|---------|---------------------|
| 🤖 **LLM Calls** | Tổng số lần gọi AI (chat + ảnh + audio) | — |
| 🛠️ **Admin Ops** | Số thao tác quản trị (reset quota, reconcile) | — |
| ⏳ **Pending** | Requests đang xử lý, chưa hoàn thành | > 10 → kiểm tra LiteLLM |
| ⚠️ **Error Rate** | Tỷ lệ lỗi (%) | > 5% → điều tra ngay |
| ⚡ **P95 Latency** | 95% requests hoàn thành trong bao lâu | > 5000ms → quá chậm |
| 🎫 **Total Tokens** | Tổng tokens đã xử lý | Theo dõi xu hướng |
| 💰 **Total Cost** | Tổng chi phí USD | So sánh với budget |

<!-- 📸 Thêm ảnh: 7 thẻ metrics trên Dashboard -->

Các thẻ này **tự động cập nhật mỗi 5 giây**, bạn không cần refresh trang.

### 13.4. Bảng Top Users

Hiển thị **10 người dùng tốn chi phí nhiều nhất**, sắp xếp giảm dần:

| Thông tin | Mô tả |
|-----------|-------|
| User ID | Tên tài khoản |
| Cost (USD) | Tổng chi phí đã dùng |

Giúp bạn phát hiện người dùng nào sử dụng quá mức hoặc cần tăng quota.

<!-- 📸 Thêm ảnh: Bảng Top Users by Cost -->

### 13.5. Bảng Top Models

Hiển thị **10 model AI được dùng nhiều nhất** theo chi phí:

Giúp bạn biết model nào phổ biến, model nào đắt, từ đó quyết định có nên hạn chế model đắt không.

<!-- 📸 Thêm ảnh: Bảng Top Models by Cost -->

### 13.6. Luồng sự kiện realtime (Recent Events)

Phía dưới Dashboard là luồng sự kiện **cập nhật trực tiếp** (realtime):

Mỗi dòng hiện:
- ⏰ **Thời gian** (giây:phút:giờ)
- 🔗 **Status**: OK (xanh lá), ERROR (đỏ), PENDING (vàng), RECONCILED (xanh dương)
- 👤 **User** dùng model nào, bao nhiêu tokens, chi phí bao nhiêu

<!-- 📸 Thêm ảnh: Luồng Recent Events đang chạy realtime -->

> 💡 Luồng sự kiện giúp bạn giám sát **đúng lúc** — nếu thấy nhiều ERROR liên tiếp, cần kiểm tra ngay.

### 13.7. Các Tab khác trên Dashboard

| Tab | Chức năng |
|-----|-----------|
| **Overview** | Tổng quan (metrics + charts + events) |
| **Logs** | Xem chi tiết log từng request (user, model, cost, timestamp) |
| **Access** | Log truy cập HTTP (method, path, status code, latency) |
| **Users** | Quản lý người dùng Middleware (xem Chương 14) |

<!-- 📸 Thêm ảnh: Các tab trên Dashboard -->

---

## Chương 14. Quản lý người dùng

Hệ thống có **2 nơi** quản lý người dùng:
- **Open WebUI Admin Panel** — quản lý tài khoản đăng nhập web (email, role)
- **Middleware Dashboard** — quản lý API key (subkey), quota, chi phí

### 14.1. Quản lý trên Open WebUI (Admin Panel)

#### Truy cập

Đăng nhập Open WebUI bằng tài khoản Admin → nhấn **Admin Panel** (⚙️ góc dưới trái) → tab **Users**.

<!-- 📸 Thêm ảnh: Admin Panel > Users trên Open WebUI -->

#### Các thao tác

| Thao tác | Cách làm |
|----------|----------|
| **Duyệt user mới** | User có status "Pending" → nhấn nút ✅ để Approve |
| **Đổi quyền** | Nhấn vào user → đổi Role: Admin / User |
| **Xóa user** | Nhấn icon 🗑️ → xác nhận |
| **Bật/tắt model** | Tab Models → bật/tắt model nào hiển thị cho user |
| **Cấu hình Knowledge** | Tab Knowledge → quản lý tất cả KB trong hệ thống |

<!-- 📸 Thêm ảnh: Duyệt user pending -->

#### Phân quyền (3 cấp)

| Vai trò | Quyền hạn |
|---------|-----------|
| **Admin** | Toàn quyền: quản lý user, model, knowledge, cài đặt hệ thống |
| **User** | Chat, upload file, dùng Knowledge, tạo workspace |
| **Pending** | Chờ duyệt — chưa thể sử dụng hệ thống |

### 14.2. Quản lý trên Middleware Dashboard

#### Truy cập

Vào Dashboard → tab **Users**.

<!-- 📸 Thêm ảnh: Tab Users trên Middleware Dashboard -->

#### Tạo user mới

1. Nhấn **"+ Add User"**
2. Điền thông tin:
   - **User ID:** Tên định danh (ví dụ: "alice")
   - **Role:** admin / user
   - **Allowed Models:** Chọn model nào user được dùng (hoặc `*` = tất cả)
   - **Quota:** Giới hạn chi phí / token / ảnh mỗi tháng
3. Nhấn **"Create"**
4. Hệ thống hiện **subkey** (mã xác thực API) — **sao chép ngay!**

<!-- 📸 Thêm ảnh: Form tạo user mới trên Dashboard -->

> ⚠️ **QUAN TRỌNG:** Subkey chỉ hiện **MỘT LẦN DUY NHẤT**. Không thể xem lại sau khi đóng popup. Hãy sao chép và lưu trữ ngay.

#### Sửa thông tin user

1. Nhấn nút **✏️ Edit** cạnh user
2. Sửa: quota, allowed models, role, period
3. Nhấn **Save**

<!-- 📸 Thêm ảnh: Form sửa user -->

#### Xoay khóa (Rotate Key)

Khi cần cấp subkey mới (ví dụ: key cũ bị lộ):

1. Nhấn nút **🔑 Rotate Key** cạnh user
2. Xác nhận → hệ thống tạo subkey mới
3. **Sao chép subkey mới** — key cũ bị vô hiệu ngay lập tức

<!-- 📸 Thêm ảnh: Popup hiện subkey mới sau khi rotate -->

#### Bật/tắt tài khoản

- Nhấn toggle **🟢/🔴** để bật/tắt user
- User bị tắt sẽ nhận lỗi **403 Forbidden** khi gọi API

<!-- 📸 Thêm ảnh: Toggle enable/disable user -->

#### Xóa user

1. Nhấn nút **🗑️ Delete**
2. Xác nhận **2 lần** (tránh xóa nhầm)
3. Xóa là vĩnh viễn

<!-- 📸 Thêm ảnh: Xác nhận xóa user 2 lần -->

---

## Chương 15. Quản lý chi phí & Quota

### 15.1. Quota là gì?

Mỗi user có một **hạn mức sử dụng** (quota) để kiểm soát chi phí. Khi hết quota, user sẽ bị chặn cho đến khi admin reset hoặc sang tháng mới.

Các loại giới hạn:

| Giới hạn | Mô tả | Ví dụ |
|----------|-------|-------|
| **limit_cost_usd** | Giới hạn chi phí (USD) / tháng | $10.00 |
| **limit_tokens** | Giới hạn tổng tokens / tháng | 500,000 |
| **limit_image_requests** | Giới hạn số lần tạo ảnh / tháng | 50 |

### 15.2. Xem chi phí hiện tại

#### Trên Dashboard

Đăng nhập Dashboard → xem ngay:
- **Total Cost** — tổng chi phí toàn hệ thống
- **Top Users by Cost** — ai tốn nhiều nhất
- **Top Models by Cost** — model nào đắt nhất

<!-- 📸 Thêm ảnh: Thẻ Total Cost và bảng Top Users -->

#### Chi tiết từng user

Vào Dashboard → tab **Users** → thấy cột **Used Cost** cho từng user.

<!-- 📸 Thêm ảnh: Bảng users với cột Used Cost -->

### 15.3. Cài đặt quota cho user

1. Dashboard → tab **Users** → nhấn **Edit** (✏️) cạnh user
2. Sửa các trường quota:
   - **Period:** monthly (tháng) hoặc daily (ngày)
   - **Limit Cost USD:** Số tiền tối đa (ví dụ: 10.00)
   - **Limit Tokens:** Tổng tokens tối đa (0 = không giới hạn)
   - **Limit Image Requests:** Số ảnh tối đa (0 = không giới hạn)
3. Nhấn **Save**

<!-- 📸 Thêm ảnh: Form sửa quota -->

### 15.4. Khi user hết quota

Khi user đạt 100% quota:
- ❌ Mọi request tiếp theo bị từ chối (**403 Forbidden**)
- 📧 User nhận email cảnh báo
- 🔔 Admin nhận thông báo trên Dashboard

### 15.5. Reset quota

Có 2 cách reset:

**Cách 1: Tự động** — Quota tự reset vào đầu mỗi tháng (hoặc mỗi ngày nếu period = daily).

**Cách 2: Thủ công** — Admin reset qua Dashboard:
1. Tab Users → nhấn Edit user
2. Reset **Used Cost** về 0
3. Save

<!-- 📸 Thêm ảnh: Reset quota thủ công -->

### 15.6. Chi phí theo nhà cung cấp (Provider Budget)

Ngoài quota per-user, admin còn theo dõi tổng chi phí theo từng nhà cung cấp API:

| Provider | Budget mặc định | Model groups |
|----------|----------------|--------------|
| **OpenAI** | $100/tháng | GPT-5, GPT-4o, DALL-E, TTS, STT |
| **Gemini** | $50/tháng | Gemini 2.5, Gemini 3, Gemini Image |

Xem chi tiết trên Dashboard → tổng hợp theo model.

<!-- 📸 Thêm ảnh: Chi phí theo provider trên Dashboard -->

---

## Chương 16. Cảnh báo tự động

Hệ thống có khả năng **tự động gửi cảnh báo** khi chi phí sắp vượt mức, giúp admin chủ động xử lý trước khi "cháy túi".

### 16.1. Hai loại cảnh báo

| Loại | Đối tượng | Khi nào kích hoạt? |
|------|-----------|---------------------|
| **Cảnh báo Quota (per-user)** | Từng user cụ thể | User dùng gần hết hoặc hết quota |
| **Cảnh báo Budget (per-provider)** | Toàn bộ hệ thống | Tổng chi phí API gần hết budget tháng |

### 16.2. Cảnh báo Quota cho User

Hệ thống tự kiểm tra sau mỗi request và gửi cảnh báo theo 3 ngưỡng:

| Ngưỡng | Hành động | Ai nhận? |
|:------:|-----------|----------|
| **80%** | 📧 Email nhắc nhở user + 🔔 Dashboard | User + Admin |
| **95%** | 📧 Email cảnh báo khẩn + 🔔 Dashboard | User + Admin |
| **100%** | 📧 Email thông báo bị chặn + ❌ **Chặn user** | User + Admin |

**Ví dụ email user nhận được:**

```
Xin chào alice,

Tài khoản của bạn đã sử dụng 95% hạn mức chi phí.

  • Đã dùng: $9.50
  • Hạn mức:  $10.00
  • Còn lại:  $0.50

Vui lòng sử dụng tiết kiệm để tránh bị chặn.
```

<!-- 📸 Thêm ảnh: Email cảnh báo quota gửi cho user -->

### 16.3. Cảnh báo Budget cho Provider

Theo dõi tổng chi phí API chung (tất cả user cộng lại):

| Provider | Ngưỡng cảnh báo | Hành động |
|----------|:---------------:|-----------|
| OpenAI | 70%, 90% | 🔔 Dashboard |
| OpenAI | 100% | 📧 Email Admin + 🔔 Dashboard |
| Gemini | 80% | 🔔 Dashboard |
| Gemini | 100% | 📧 Email Admin + 🔔 Dashboard |

> ⚠️ **Lưu ý:** Hệ thống **KHÔNG tự chặn** khi budget hết (vì sẽ ảnh hưởng tất cả user). Admin cần tự quyết định: nạp thêm tiền hoặc tăng budget.

<!-- 📸 Thêm ảnh: Notification cảnh báo budget trên Dashboard -->

### 16.4. Bell icon — Chuông thông báo trên Dashboard

- 🔔 **Bell icon** hiện ở góc trên phải Dashboard
- **Badge đỏ** cho biết số thông báo chưa đọc
- Nhấn vào để xem danh sách cảnh báo
- Nhấn vào từng mục để đánh dấu "đã đọc"
- Nút **"✓ Tất cả"** để đánh dấu tất cả đã đọc

<!-- 📸 Thêm ảnh: Bell icon với dropdown danh sách notifications -->

### 16.5. Email tổng hợp hàng ngày (Daily Digest)

Mỗi sáng lúc **8:00 AM**, hệ thống tự động gửi email tổng hợp cho admin:

1. Tổng cảnh báo 24h qua (critical / warning / info)
2. Bảng quota toàn bộ users (ai dùng bao nhiêu %)
3. Chi phí theo provider (OpenAI / Gemini)

<!-- 📸 Thêm ảnh: Ví dụ email Daily Digest -->

---

## Chương 17. Bảo mật & Quản lý Key

### 17.1. Tổng quan bảo mật

Hệ thống được thiết kế với **nhiều lớp bảo mật**:

| Lớp | Biện pháp |
|-----|-----------|
| **Mạng** | Chỉ 1 port mở (3000 qua Nginx HTTPS). Tất cả service khác đóng kín |
| **Đăng nhập** | Email/Password + JWT token (Open WebUI) |
| **API** | Subkey mã hóa HMAC-SHA256 (Middleware) |
| **Dashboard** | Admin Key + JWT cookie (HttpOnly, 4h hết hạn) |
| **Dữ liệu** | Embedding chạy 100% local — tài liệu nội bộ không ra ngoài |
| **Rate Limit** | Nginx giới hạn 10 req/s (chat), 5 req/phút (login) |

<!-- 📸 Thêm ảnh: Sơ đồ bảo mật nhiều lớp -->

### 17.2. Subkey là gì?

**Subkey** là mã xác thực API riêng cho mỗi user. Nó giống như "chìa khóa" để user gọi API AI qua Middleware.

- Dạng: `sk_abc123def456...`
- Được mã hóa **HMAC-SHA256** — không thể dịch ngược
- Chỉ hiện **1 lần** khi tạo hoặc rotate → phải sao chép ngay
- Dashboard chỉ hiện hash rút gọn (`abc...xyz`)

### 17.3. Quy trình quản lý Key

| Tình huống | Hành động |
|-----------|-----------|
| Tạo user mới | Hệ thống tự cấp subkey → sao chép cho user |
| Key bị lộ / nghi bị lộ | **Rotate Key** ngay → key cũ bị hủy tức thì |
| User nghỉ việc | Disable tài khoản hoặc xóa user |
| Định kỳ | Rotate key mỗi 90 ngày (khuyến nghị) |

<!-- 📸 Thêm ảnh: Nút Rotate Key trên Dashboard -->

### 17.4. Lưu ý về dữ liệu

| Loại dữ liệu | Gửi ra ngoài? | Giải thích |
|--------------|:-------------:|------------|
| Nội dung chat (prompt + response) | ✅ Có | Gửi đến OpenAI/Google để xử lý — đây là bản chất của LLM cloud |
| Tài liệu Knowledge Base | ❌ Không | Embedding chạy 100% trên server nội bộ |
| Database (chat history, users) | ❌ Không | Lưu trên PostgreSQL trong Docker, không dùng cloud DB |
| Vector embeddings | ❌ Không | Lưu trên PGVector (PostgreSQL), nội bộ |

> 💡 **Giải thích:** Khi bạn dùng RAG (#KB), AI chỉ nhận các "đoạn trích nhỏ" liên quan từ tài liệu, không phải toàn bộ file. Bản gốc tài liệu luôn ở trên server.

---

## Chương 18. Vận hành hệ thống & FAQ

### 18.1. Kiểm tra sức khỏe hệ thống

| Kiểm tra | Cách làm |
|----------|----------|
| Tất cả service đang chạy? | `docker compose ps` — tất cả 8 container phải ở trạng thái "running" |
| Dashboard hoạt động? | Truy cập `/dashboard` → phải hiện màn login |
| API hoạt động? | Gọi `curl https://openwebui.example.com:51122/v1/models` |

<!-- 📸 Thêm ảnh: Kết quả docker compose ps - tất cả healthy -->

### 18.2. Thao tác định kỳ

| Tần suất | Việc cần làm |
|----------|-------------|
| **Hàng ngày** | Duyệt user pending (Admin Panel > Users) |
| **Hàng ngày** | Kiểm tra Dashboard — xem error rate, chi phí |
| **Hàng tuần** | Review chi phí per user — ai dùng quá nhiều? |
| **Hàng tuần** | Kiểm tra `docker compose ps` — tất cả healthy? |
| **Hàng tháng** | Backup database |
| **Hàng tháng** | Review và điều chỉnh quota theo nhu cầu thực tế |

### 18.3. Backup database

```bash
# Backup database Open WebUI
docker exec openwebui-postgres pg_dump -U openwebui_user -d openwebui > backup_openwebui.sql

# Backup database Middleware
docker exec openwebui-postgres pg_dump -U openwebui_user -d middleware > backup_middleware.sql
```

### 18.4. Khởi động lại hệ thống

| Thao tác | Lệnh |
|----------|------|
| Restart tất cả | `docker compose restart` |
| Restart 1 service | `docker compose restart middleware` |
| Dừng + chạy lại | `docker compose down && docker compose up -d` |
| Xem log | `docker compose logs -f middleware` |

### 18.5. Câu hỏi thường gặp (FAQ)

#### ❓ User đăng ký nhưng không đăng nhập được?

**Trả lời:** Tài khoản mới ở trạng thái "Pending". Admin cần vào Admin Panel → Users → nhấn ✅ Approve.

#### ❓ User báo "Lỗi khi gửi tin nhắn"?

**Trả lời:** Kiểm tra:
1. User có bị hết quota không? (Dashboard → Users → xem Used Cost)
2. Model có đang bật không? (Admin Panel → Models)
3. LiteLLM có đang chạy không? (`docker compose ps`)

#### ❓ Làm sao biết chi phí tháng này bao nhiêu?

**Trả lời:** Vào Dashboard → thẻ **Total Cost** hiện tổng chi phí. Xem bảng Top Users và Top Models để biết chi tiết.

#### ❓ User quên mật khẩu Open WebUI?

**Trả lời:** Admin vào Admin Panel → Users → nhấn vào user → Reset Password.

#### ❓ Tài liệu upload lên Knowledge Base có bị gửi ra ngoài không?

**Trả lời:** **Không.** Tài liệu được xử lý 100% trên server nội bộ. Chỉ có câu hỏi và trích đoạn nhỏ liên quan mới được gửi cho AI để trả lời.

#### ❓ Subkey bị mất, làm sao lấy lại?

**Trả lời:** Không thể lấy lại subkey cũ (đã mã hóa một chiều). Admin cần vào Dashboard → Users → **Rotate Key** để cấp subkey mới.

#### ❓ Model nào nên dùng để tiết kiệm nhất?

**Trả lời:** `mm-gemini-2.5-flash` — nhanh, chất lượng tốt, chi phí thấp nhất trong nhóm "tốt".

#### ❓ Có thể dùng trên điện thoại không?

**Trả lời:** Có. Open WebUI là web responsive — mở bằng trình duyệt trên điện thoại là dùng được, không cần cài app.

#### ❓ Dashboard bị lỗi "Invalid admin key"?

**Trả lời:** Kiểm tra Admin Key có đúng không (trong file `.env`, biến `ADMIN_KEY`). Nếu đúng mà vẫn lỗi, thử restart middleware: `docker compose restart middleware`.

#### ❓ Muốn thêm model AI mới?

**Trả lời:** Liên hệ đội kỹ thuật. Model mới được cấu hình trong file `litellm/litellm_config.yaml` và cần restart service.

---

## 📌 Tra cứu nhanh

### Địa chỉ truy cập

| Dịch vụ | URL |
|---------|-----|
| Open WebUI (Chat) | `https://openwebui.example.com:51122/` |
| Dashboard (Admin) | `https://openwebui.example.com:51122/dashboard` |
| Nội bộ LAN | `https://10.0.0.1:3000/` |

### Model khuyến nghị

| Mục đích | Model |
|----------|-------|
| Chat hàng ngày | `mm-gemini-2.5-flash` |
| Phân tích sâu | `mm-gpt-5` |
| Tài liệu dài | `mm-gpt-4.1` |
| Tạo ảnh | `img-gemini-flash` |

### Phím tắt / Ký hiệu

| Ký hiệu | Ý nghĩa |
|----------|---------|
| `#` | Gọi Knowledge Base hoặc file trong chat |
| `/` | Gọi Saved Prompt |
| `Enter` | Gửi tin nhắn |
| `Shift + Enter` | Xuống dòng (không gửi) |

---

*Tài liệu được tạo ngày 31/03/2026. Mọi thắc mắc liên hệ đội kỹ thuật AI.*
