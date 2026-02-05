# Hướng Dẫn Test Open WebUI Stack (Chi Tiết)

## ✅ Kết Quả Test Tự Động
**14/14 tests PASSED** trong ~60 giây

---

## 🔐 Thông Tin Đăng Nhập

| Tài Khoản | Giá Trị |
|-----------|---------|
| **Admin Email** | adminrd@gmail.com |
| **Admin Password** | Testcus1234 |
| Middleware Subkey | subkey_admin_123 |
| LiteLLM Master Key | super_admin_key_123 |

---

## 🖥️ HƯỚNG DẪN TEST UI (THỦ CÔNG)

### Bước 1: Mở Open WebUI
1. Mở trình duyệt (Chrome/Firefox/Edge)
2. Truy cập: **http://localhost:3000**
3. Trang login sẽ hiển thị

### Bước 2: Đăng Nhập Admin
1. Nhập Email: `adminrd@gmail.com`
2. Nhập Password: `Testcus1234`
3. Click **Sign In**
4. ✅ **Kết quả mong đợi**: Chuyển đến giao diện chat

### Bước 3: Kiểm Tra Giao Diện Chính
Sau khi đăng nhập, kiểm tra các thành phần:

| Thành Phần | Vị Trí | Mô Tả |
|------------|--------|-------|
| **Sidebar** | Bên trái | Menu navigation, danh sách chat |
| **Chat Input** | Dưới cùng | Ô nhập tin nhắn |
| **Model Selector** | Góc trên | Dropdown chọn AI model |
| **New Chat** | Sidebar | Nút tạo chat mới |
| **Settings** | Avatar/menu | Link đến cài đặt |

### Bước 4: Test Chat Cơ Bản
1. Click **New Chat** (nếu cần)
2. Trong ô chat, nhập: `Hello, can you hear me?`
3. Nhấn Enter hoặc click Send
4. ✅ **Kết quả mong đợi**: AI trả lời tin nhắn

### Bước 5: Test Model Selection
1. Click dropdown **Model Selector** (góc trên)
2. Xem danh sách models có sẵn:
   - `gpt-4o-mini` (OpenAI)
   - `gemini-1.5-flash` (Google)
   - Các model khác (nếu cấu hình)
3. Chọn model khác và gửi tin nhắn
4. ✅ **Kết quả mong đợi**: Chat hoạt động với model mới

### Bước 6: Test Admin Settings
1. Click Avatar (góc trên phải) → **Admin Panel** hoặc **Settings**
2. Truy cập: http://localhost:3000/admin/settings
3. Kiểm tra các tab:
   - **General**: Cài đặt chung
   - **Users**: Quản lý người dùng
   - **Connections**: LLM connections
   - **Models**: Quản lý models
4. ✅ **Kết quả mong đợi**: Có thể xem/chỉnh sửa settings

### Bước 7: Test RAG/Knowledge Base
1. Truy cập: http://localhost:3000/workspace/knowledge
2. Click **Create Knowledge Base**
3. Đặt tên: "Test KB"
4. Upload file test (PDF, TXT, DOCX)
5. Đợi xử lý xong
6. Quay lại Chat, chọn Knowledge Base vừa tạo
7. Hỏi câu hỏi liên quan đến nội dung file
8. ✅ **Kết quả mong đợi**: AI trả lời dựa trên nội dung file

---

## 🔌 TEST API (MIDDLEWARE)

### Test với PowerShell

```powershell
# 1. Lấy danh sách models
Invoke-RestMethod -Uri "http://localhost:5000/v1/models" `
    -Headers @{"Authorization"="Bearer subkey_admin_123"}

# 2. Test chat completion
$body = @{
    model = "gpt-4o-mini"
    messages = @(@{role="user"; content="Say hello"})
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "http://localhost:5000/v1/chat/completions" `
    -Method POST `
    -Headers @{"Authorization"="Bearer subkey_admin_123"; "Content-Type"="application/json"} `
    -Body $body
```

### Test với cURL

```bash
# Health check LiteLLM
curl http://localhost:4000/health

# Models list
curl -H "Authorization: Bearer subkey_admin_123" http://localhost:5000/v1/models
```

---

## 🗄️ TEST DATABASE (PostgreSQL)

### Kết nối vào PostgreSQL

```powershell
docker exec -it openwebui-postgres psql -U openwebui_user -d openwebui
```

### Các lệnh SQL kiểm tra

```sql
-- Kiểm tra PGVector extension
\dx

-- Liệt kê tất cả tables
\dt

-- Đếm số users
SELECT count(*) FROM "user";

-- Xem user admin
SELECT id, email, name, role FROM "user" WHERE email = 'adminrd@gmail.com';

-- Kiểm tra documents (RAG)
SELECT id, name, filename, created_at FROM document LIMIT 10;

-- Kiểm tra chat history
SELECT id, title, created_at FROM chat ORDER BY created_at DESC LIMIT 5;
```

---

## 🧪 CHẠY PLAYWRIGHT TESTS

### Các lệnh hay dùng

```powershell
cd D:\Works\Open_Web_UI\Oppen_Web_UI\tests

# Chạy tất cả tests (headless)
npx playwright test

# Chạy tests với browser hiển thị
npx playwright test --headed

# Chạy Playwright UI (interactive)
npx playwright test --ui

# Chạy một test file cụ thể
npx playwright test auth.spec.ts

# Xem report HTML sau khi test
npx playwright show-report
```

---

## 🔧 TROUBLESHOOTING

### Container không chạy
```powershell
docker-compose logs [service-name]
docker-compose restart [service-name]
```

### Kiểm tra status tất cả services
```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Reset hoàn toàn (⚠️ XÓA DỮ LIỆU)
```powershell
docker-compose down -v
docker-compose up -d
```

### Xem logs real-time
```powershell
docker-compose logs -f openwebui-app
```

---

## 📊 CHECKLIST TEST

### UI Tests
- [ ] Login page loads
- [ ] Login with admin credentials
- [ ] Chat interface displays
- [ ] Send message and receive response
- [ ] Switch between models
- [ ] Access admin settings
- [ ] Create knowledge base
- [ ] Upload document
- [ ] Query with RAG

### API Tests
- [ ] GET /v1/models works
- [ ] POST /v1/chat/completions works
- [ ] Authentication rejected with invalid key

### Database Tests
- [ ] PostgreSQL connection works
- [ ] PGVector extension installed
- [ ] User table has data
- [ ] Document table exists
