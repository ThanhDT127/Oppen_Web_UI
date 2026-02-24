# Hướng Dẫn Triển Khai Export Tool (PDF/Excel/Word) trên Máy Ảo

> **Đường dẫn code trên VM:** `C:\Code\openwebui_fetch\Oppen_Web_UI`

---

## Chuẩn bị

Bạn cần 2 file từ máy dev:
1. `tool_export_all.py` — code tool export
2. File hướng dẫn này

---

## Bước 1: Tạo file `Dockerfile.openwebui`

Tạo file `C:\Code\openwebui_fetch\Oppen_Web_UI\Dockerfile.openwebui` với nội dung:

```dockerfile
FROM ghcr.io/open-webui/open-webui:main

USER root

# 1. Cài đầy đủ font DejaVu (core = Regular+Bold, extra = Oblique+BoldOblique)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    fonts-dejavu-extra && \
    rm -rf /var/lib/apt/lists/*

# 2. Cài sẵn pip dependencies cho tool export
RUN pip install --no-cache-dir \
    "fpdf2>=2.7" \
    "openpyxl>=3.1" \
    "python-docx>=1.1" \
    "requests>=2.28"

# 3. Đảm bảo cache/functions directory có đúng quyền
RUN mkdir -p /app/backend/data/cache/functions && \
    chown -R 1000:0 /app/backend/data/cache

USER 1000
```

---

## Bước 2: Chỉnh `docker-compose.yml`

Mở `C:\Code\openwebui_fetch\Oppen_Web_UI\docker-compose.yml`, tìm service `open-webui`.

### 2a. Đổi `image:` thành `build:`

**Trước:**
```yaml
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
```

**Sau:**
```yaml
  open-webui:
    build:
      context: .
      dockerfile: Dockerfile.openwebui
```

> ⚠️ Giữ nguyên tất cả phần khác (environment, volumes, ports, depends_on...). Chỉ thay dòng `image:` bằng block `build:`.

### 2b. (Tuỳ chọn) Xoá dòng `version:` nếu có

Nếu file có dòng `version: "3.x"` ở đầu, có thể xoá để tránh warning.

---

## Bước 3: Fix quyền volume (chạy 1 lần duy nhất)

Nếu đã từng chạy Open WebUI trước đó, volume data có thể bị sai quyền. Chạy lệnh sau để fix:

```powershell
# Tìm tên volume đúng
docker volume ls
```

Tìm volume có tên giống `oppen_web_ui_openwebui_data` hoặc tương tự, rồi chạy:

```powershell
docker run --rm -v <TEN_VOLUME>:/data alpine chown -R 1000:0 /data
```

**Ví dụ:**
```powershell
docker run --rm -v oppen_web_ui_openwebui_data:/data alpine chown -R 1000:0 /data
```

> Nếu chưa từng chạy Open WebUI → bỏ qua bước này.

---

## Bước 4: Build Docker image

```powershell
cd C:\Code\openwebui_fetch\Oppen_Web_UI
docker compose build --no-cache open-webui
```

Chờ build xong (~2-5 phút).

---

## Bước 5: Khởi động

```powershell
docker compose up -d open-webui
```

Kiểm tra:
```powershell
docker compose ps
docker logs openwebui-app --tail 30
```

Chờ đến khi log hiện `Uvicorn running on http://0.0.0.0:8080` hoặc tương tự.

---

## Bước 6: Thêm tool vào Open WebUI

1. Mở browser → `http://<IP_VM>:3000`
2. Đăng nhập Admin
3. Vào **Admin Panel** → **Functions** → **Create New Function**
4. Đặt tên: `Xuất File (PDF / Excel / Word)` (hoặc tuỳ ý)
5. Chọn Type: **Action**
6. **Copy toàn bộ** nội dung file `tool_export_all.py` → **Paste** vào editor code
7. Nhấn **Save**

---

## Bước 7: Kiểm tra

1. Mở 1 chat bất kỳ, gõ gì đó để bot trả lời
2. Nhấn nút **Action** (⚡) bên dưới tin nhắn bot
3. Chọn **Xuất File**
4. Chọn format (1=Excel, 2=PDF, 3=Word)
5. Đợi file tải xuống

### Test tiếng Việt:
- Gõ: *"Tạo bảng 5 tỉnh thành Việt Nam với dân số"*
- Export PDF → kiểm tra font tiếng Việt hiển thị đúng (không bị ô vuông □□□)

---

## Xử lý lỗi thường gặp

| Lỗi | Nguyên nhân | Cách fix |
|-----|-------------|----------|
| `TTF Font file not found` | Thiếu package fonts trong Docker | Build lại: `docker compose build --no-cache open-webui` |
| `Permission denied: cache/functions` | Volume sai quyền | Chạy lại Bước 3 |
| `ModuleNotFoundError: fpdf` | pip chưa cài trong container | Kiểm tra Dockerfile có đúng `pip install` không, build lại |
| Tool không hiện trong chat | Chưa Save hoặc chưa bật | Vào Admin → Functions → kiểm tra đã Save và Enable |
| Không kết nối được web | Port chưa mở | Kiểm tra `docker compose ps`, đảm bảo port 3000 đang map |

---

## Tóm tắt file cần có

```
C:\Code\openwebui_fetch\Oppen_Web_UI\
├── docker-compose.yml          ← chỉnh build: thay image:
├── Dockerfile.openwebui        ← TẠO MỚI (nội dung ở Bước 1)
├── .env                        ← giữ nguyên (passwords, keys)
├── function tool\
│   └── tool_export_all.py      ← COPY TỪ MÁY DEV
└── ... (các file khác giữ nguyên)
```
