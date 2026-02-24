# Hướng Dẫn Cấu Hình Image Generation trong OpenWebUI

## Tổng Quan Kiến Trúc

```
OpenWebUI (Port 3000)
    ↓ HTTP Request
Middleware (Port 5000) - Xác thực & Quota
    ↓ Forward request
LiteLLM (Port 4000) - Proxy
    ↓ API Call
OpenAI DALL-E 3 hoặc Gemini Image Generation
```

## 📋 Yêu Cầu

- ✅ OpenWebUI đang chạy
- ✅ Middleware đang chạy (port 5000)
- ✅ LiteLLM đang chạy (port 4000)
- ✅ Có API key OpenAI hoặc Gemini hợp lệ trong `.env`
- ✅ Model image generation đã được cấu hình trong `litellm/litellm_config.yaml`

## 🎨 Models Tạo Ảnh Hiện Có

Trong file `litellm/litellm_config.yaml` đã có 2 models:

### 1. OpenAI DALL-E 3
```yaml
- model_name: gpt-image-1
  litellm_params:
    model: openai/dall-e-3
    api_key: os.environ/OPENAI_API_KEY
```

### 2. Gemini Image Generation
```yaml
- model_name: gemini-2.5-flash-image
  litellm_params:
    model: gemini/gemini-2.5-flash-image
    api_key: os.environ/GEMINI_API_KEY
```

## 🔧 Cấu Hình OpenWebUI

### Bước 1: Mở Settings trong OpenWebUI

1. Truy cập OpenWebUI: `http://localhost:3000`
2. Click vào **Settings** (biểu tượng bánh răng)
3. Chọn **Images** trong menu bên trái

### Bước 2: Cấu Hình Image Generation API

#### **Option A: Sử dụng OpenAI DALL-E 3 (qua Middleware)**

Trong OpenWebUI Settings > Images:

```
┌─────────────────────────────────────────┐
│ Image Generation Engine                 │
├─────────────────────────────────────────┤
│ [x] Enable Image Generation             │
│                                         │
│ API Type: OpenAI                        │
│                                         │
│ Base URL:                               │
│ http://127.0.0.1:5000/v1               │
│                                         │
│ API Key:                                │
│ YOUR_SUBKEY_ADMIN                        │
│                                         │
│ Image Generation Model:                 │
│ gpt-image-1                            │
│                                         │
│ Image Size:                             │
│ 1024x1024                              │
└─────────────────────────────────────────┘
```

**Chi tiết cấu hình:**
- **Enable Image Generation**: ✅ Bật
- **API Type**: `OpenAI`
- **Base URL**: `http://127.0.0.1:5000/v1` (trỏ vào Middleware)
- **API Key**: `YOUR_SUBKEY_ADMIN` (hoặc `YOUR_SUBKEY_USER1`)
- **Model**: `gpt-image-1` (tên model trong litellm_config.yaml)
- **Image Size**: 
  - DALL-E 3 hỗ trợ: `1024x1024`, `1792x1024`, `1024x1792`
  - DALL-E 2 hỗ trợ: `256x256`, `512x512`, `1024x1024`

#### **Option B: Sử dụng Gemini (qua Middleware)**

```
┌─────────────────────────────────────────┐
│ Image Generation Engine                 │
├─────────────────────────────────────────┤
│ [x] Enable Image Generation             │
│                                         │
│ API Type: OpenAI                        │
│                                         │
│ Base URL:                               │
│ http://127.0.0.1:5000/v1               │
│                                         │
│ API Key:                                │
│ YOUR_SUBKEY_ADMIN                        │
│                                         │
│ Image Generation Model:                 │
│ gemini-2.5-flash-image                 │
│                                         │
│ Image Size:                             │
│ 1024x1024                              │
└─────────────────────────────────────────┘
```

### Bước 3: Cấu Hình Truy Cập Từ Mạng Ngoài

Nếu OpenWebUI được truy cập từ máy khác trong mạng LAN:

```
Base URL: http://192.168.20.92:5000/v1
```

⚠️ **LƯU Ý**: Thay `192.168.20.92` bằng IP thực tế của máy server (xem khi chạy `.\scripts\start.ps1`)

## 🧪 Kiểm Tra Cấu Hình

### Test 1: Kiểm tra model có trong danh sách

```powershell
# Activate venv
C:\Code\.venv\Scripts\Activate.ps1

# Kiểm tra danh sách models
$response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/v1/models" `
    -Headers @{"Authorization"="Bearer YOUR_SUBKEY_ADMIN"} `
    -UseBasicParsing
$response.Content | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-Object id
```

**Kết quả mong đợi**: Phải thấy `gpt-image-1` và `gemini-2.5-flash-image` trong danh sách

### Test 2: Gọi API tạo ảnh trực tiếp

```powershell
# Test DALL-E 3 qua Middleware
$body = @{
    model = "gpt-image-1"
    prompt = "A beautiful sunset over the ocean"
    n = 1
    size = "1024x1024"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/v1/images/generations" `
    -Method POST `
    -Headers @{
        "Authorization" = "Bearer YOUR_SUBKEY_ADMIN"
        "Content-Type" = "application/json"
    } `
    -Body $body `
    -UseBasicParsing

$response.Content | ConvertFrom-Json
```

**Kết quả mong đợi**: JSON response với URL ảnh

```json
{
  "created": 1677610602,
  "data": [
    {
      "url": "https://oaidalleapiprodscus.blob.core.windows.net/..."
    }
  ]
}
```

### Test 3: Sử dụng trong OpenWebUI

1. Mở chat mới trong OpenWebUI
2. Gõ lệnh: `/image` hoặc click biểu tượng 🎨
3. Nhập prompt: "A beautiful sunset over the ocean"
4. Click **Generate**
5. Ảnh sẽ được tạo và hiển thị trong chat

## 🔐 Quản Lý API Keys

### Subkeys trong Middleware

File: `llm-mw\data\users.json`

```json
[
  {
    "user_id": "admin",
    "subkey": "YOUR_SUBKEY_ADMIN",
    "active": true,
    "allowed_models": ["*"],
    "quota": {
      "limit_tokens": 0,
      "limit_cost_usd": 0
    }
  },
  {
    "user_id": "user1",
    "subkey": "YOUR_SUBKEY_USER1",
    "active": true,
    "allowed_models": ["*"],
    "quota": {
      "limit_tokens": 200000,
      "limit_cost_usd": 10.0
    }
  }
]
```

**Subkey nào dùng?**
- `YOUR_SUBKEY_ADMIN`: Không giới hạn quota (admin)
- `YOUR_SUBKEY_USER1`: Giới hạn 200k tokens/tuần, $10 USD

### Thêm Model Mới vào LiteLLM Config

Để thêm model image generation khác, edit file `litellm/litellm_config.yaml`:

```yaml
# DALL-E 2 (rẻ hơn DALL-E 3)
- model_name: gpt-image-2
  litellm_params:
    model: openai/dall-e-2
    api_key: os.environ/OPENAI_API_KEY

# Stable Diffusion (nếu có server AUTOMATIC1111)
- model_name: stable-diffusion
  litellm_params:
    model: openai/stabilityai/stable-diffusion-xl-base-1.0
    api_key: os.environ/STABILITY_API_KEY
```

Sau khi sửa config, restart LiteLLM:
```powershell
.\scripts\stop.ps1
.\scripts\start.ps1
```

## 🎛️ Advanced Settings

### Tùy Chỉnh Prompt Tạo Ảnh

OpenWebUI hỗ trợ các tham số nâng cao:

- **Quality**: `standard` hoặc `hd` (chỉ DALL-E 3)
- **Style**: `vivid` hoặc `natural` (chỉ DALL-E 3)
- **Steps**: Số bước sinh ảnh (Stable Diffusion)

### Auto Image Description

OpenWebUI có thể tự động mô tả ảnh được tạo ra bằng GPT-4V:

Settings > Images > Enable Auto Image Description

## 🐛 Troubleshooting

### Lỗi "Invalid or inactive sub-key"

**Nguyên nhân**: Dùng sai API key

**Giải pháp**:
- ❌ Không dùng: `YOUR_LITELLM_KEY`, `LITELLM_KEY`
- ✅ Phải dùng: `YOUR_SUBKEY_ADMIN` hoặc `YOUR_SUBKEY_USER1`

### Lỗi "Model not found"

**Nguyên nhân**: Model name không khớp với litellm_config.yaml

**Giải pháp**:
1. Kiểm tra tên model trong file `litellm/litellm_config.yaml`
2. Dùng đúng tên `gpt-image-1` hoặc `gemini-2.5-flash-image`
3. Restart LiteLLM nếu vừa sửa config

### Lỗi "Connection refused"

**Nguyên nhân**: Service chưa chạy

**Giải pháp**:
```powershell
# Kiểm tra các service có chạy không
Get-NetTCPConnection -LocalPort 3000,4000,5000 -ErrorAction SilentlyContinue

# Nếu không có, khởi động lại
.\scripts\start.ps1
```

### Ảnh không hiển thị trong OpenWebUI

**Nguyên nhân**: URL ảnh không accessible hoặc CORS issue

**Giải pháp**:
1. Kiểm tra response có chứa URL ảnh hợp lệ
2. Thử mở URL trực tiếp trong browser
3. Kiểm tra console log trong OpenWebUI (F12)

### Chi Phí Quá Cao

**Giải pháp**:
1. Dùng DALL-E 2 thay vì DALL-E 3 (rẻ hơn 10x)
2. Giảm kích thước ảnh: `256x256` hoặc `512x512`
3. Set quota limit trong `users.json`

## 📊 Giá Tham Khảo (OpenAI)

| Model | Kích Thước | Giá |
|-------|-----------|-----|
| DALL-E 3 Standard | 1024×1024 | $0.040/ảnh |
| DALL-E 3 Standard | 1024×1792, 1792×1024 | $0.080/ảnh |
| DALL-E 3 HD | 1024×1024 | $0.080/ảnh |
| DALL-E 3 HD | 1024×1792, 1792×1024 | $0.120/ảnh |
| DALL-E 2 | 1024×1024 | $0.020/ảnh |
| DALL-E 2 | 512×512 | $0.018/ảnh |
| DALL-E 2 | 256×256 | $0.016/ảnh |

## 📝 Example Usage trong Code

### Python
```python
import requests

response = requests.post(
    "http://127.0.0.1:5000/v1/images/generations",
    headers={
        "Authorization": "Bearer YOUR_SUBKEY_ADMIN",
        "Content-Type": "application/json"
    },
    json={
        "model": "gpt-image-1",
        "prompt": "A futuristic city at sunset",
        "n": 1,
        "size": "1024x1024"
    }
)

image_url = response.json()["data"][0]["url"]
print(f"Image URL: {image_url}")
```

### cURL
```bash
curl http://127.0.0.1:5000/v1/images/generations \
  -H "Authorization: Bearer YOUR_SUBKEY_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-1",
    "prompt": "A futuristic city at sunset",
    "n": 1,
    "size": "1024x1024"
  }'
```

## 🔗 Resources

- [OpenWebUI Documentation](https://docs.openwebui.com/)
- [LiteLLM Image Generation](https://docs.litellm.ai/docs/image_generation)
- [OpenAI DALL-E API](https://platform.openai.com/docs/guides/images)
- [Gemini Vision](https://ai.google.dev/gemini-api/docs/vision)

## ✅ Checklist Cấu Hình

- [ ] Services đang chạy (LiteLLM, Middleware, OpenWebUI)
- [ ] API keys hợp lệ trong `.env`
- [ ] Model image trong `litellm_config.yaml`
- [ ] OpenWebUI Settings > Images đã cấu hình
- [ ] Base URL trỏ đúng: `http://127.0.0.1:5000/v1`
- [ ] API Key dùng subkey: `YOUR_SUBKEY_ADMIN`
- [ ] Model name đúng: `gpt-image-1` hoặc `gemini-2.5-flash-image`
- [ ] Test API trực tiếp thành công
- [ ] Test trong OpenWebUI UI thành công

---

**Tác giả**: GitHub Copilot  
**Ngày tạo**: 15/01/2026  
**Phiên bản**: 1.0
