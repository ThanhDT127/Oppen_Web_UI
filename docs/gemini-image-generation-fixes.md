# Sửa lỗi Gemini Image Generation

> **Ngày**: 2026-02-07  
> **Files sửa**: `llm-mw/api/images.py`, `llm-mw/api/chat.py`, `litellm/litellm_config.yaml`

---

## 1. Tổng quan vấn đề

Khi tạo ảnh qua Gemini trong Open WebUI, gặp 2 lỗi chính:
- **404 Not Found** – LiteLLM không hỗ trợ Gemini image qua endpoint `/v1/images/generations`
- **"Chunk too big"** – Open WebUI không render được base64 image data quá lớn trong streaming response

---

## 2. Nguyên nhân gốc (Root Cause)

### 2.1. Sai model name trong LiteLLM config

**Trước (sai):**
```yaml
model_name: img-gemini-flash
litellm_params:
  model: gemini/gemini-2.0-flash-preview-image-generation  # Model không tồn tại
```

**Sau (đúng):**
```yaml
model_name: img-gemini-flash
litellm_params:
  model: gemini/gemini-2.5-flash-image  # Model chính xác từ Google API
```

> **Cách xác nhận**: Gọi trực tiếp Google API để list models:
> ```
> GET https://generativelanguage.googleapis.com/v1beta/models?key=<API_KEY>
> ```
> Models hỗ trợ image generation: `gemini-2.5-flash-image`, `gemini-3-pro-image-preview`

### 2.2. LiteLLM không hỗ trợ Gemini qua endpoint `/images/generations`

LiteLLM **chỉ** hỗ trợ Gemini image generation qua `/chat/completions` (nội bộ gọi `generateContent` API). Middleware trước đó gọi `/images/generations` → LiteLLM trả 404.

### 2.3. Middleware không detect `img-` prefix là image model

Hàm `_is_image_generation_model()` trong `chat.py` kiểm tra các pattern `image`, `dall-e`, `dalle`... nhưng **thiếu** `img-`. Kết quả: model `img-gemini-flash` bị forward thẳng qua `/chat/completions` → Gemini trả base64 image khổng lồ → Open WebUI báo "Chunk too big".

### 2.4. Bug `resp = None` khi dùng Gemini path

Khi gọi Gemini qua `_generate_via_gemini_chat()`, hàm này trả `data` nhưng không trả `resp` object. Code sau đó cố truy cập `resp.status_code` và `resp.headers` → crash `AttributeError: 'NoneType' object has no attribute 'status_code'`.

---

## 3. Các fix đã thực hiện

### 3.1. Sửa model name trong `litellm_config.yaml`

```diff
 - model_name: img-gemini-flash
   litellm_params:
-    model: gemini/gemini-2.0-flash-preview-image-generation
+    model: gemini/gemini-2.5-flash-image

 - model_name: img-gemini-pro
   litellm_params:
-    model: gemini/gemini-2.0-flash-preview-image-generation
+    model: gemini/gemini-3-pro-image-preview
```

### 3.2. Viết lại `_generate_via_gemini_chat()` trong `images.py`

- Route Gemini image qua `/chat/completions` thay vì `/images/generations`
- Disable streaming (`"stream": False`) – bắt buộc cho image generation
- Extract image từ LiteLLM response format v1.81.8:
  ```json
  {
    "choices": [{
      "message": {
        "content": [
          {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
        ]
      }
    }]
  }
  ```
- Fallback cho LiteLLM versions cũ hơn (kiểm tra `message.images`)

### 3.3. Sửa `_is_image_generation_model()` trong `chat.py`

```diff
 return any(pattern in model_lower for pattern in [
     "image", "dall-e", "dalle", "stable-diffusion", "midjourney", "imagen",
-    "-draw", "draw-"
+    "-draw", "draw-",
+    "img-"  # detect models like img-gemini-flash, img-gpt-dalle-3
 ])
```

### 3.4. Sửa `_handle_image_as_chat()` trong `chat.py`

Route Gemini image models qua `_generate_via_gemini_chat` thay vì gọi `/images/generations`:

```python
if "gemini" in model.lower():
    from api.images import _generate_via_gemini_chat
    image_data = await _generate_via_gemini_chat(client, headers, prompt, model)
else:
    resp = await client.post(f"{LITELLM_BASE}/images/generations", ...)
```

### 3.5. Fix 4 chỗ `resp = None` trong `images.py`

| Dòng | Trước | Sau |
|------|-------|-----|
| 326 | `resp.status_code` | `resp.status_code if resp else 200` |
| 327 | `dict(resp.headers)` | `dict(resp.headers) if resp else {}` |
| 343 | `get_cost_from_headers(resp.headers)` | `... if resp else 0` |
| 362, 388 | `resp.status_code` | `resp.status_code if resp else 200` |

---

## 4. Nhầm lẫn trong quá trình sửa

1. **Dùng sai model name ban đầu**: `gemini-2.0-flash-preview-image-generation` – model này không tồn tại trên Google API. Phải list models trực tiếp từ API mới tìm ra tên chính xác.

2. **Không sửa hết `resp.status_code`**: Lần đầu chỉ fix 2/4 chỗ, deploy lên vẫn crash. Phải grep toàn bộ file mới tìm hết.

3. **Không phát hiện `_is_image_generation_model` thiếu pattern `img-`**: Mất thời gian debug "Chunk too big" vì tưởng lỗi ở LiteLLM, nhưng thực ra middleware không detect đúng model → forward thẳng qua chat → base64 quá lớn.

---

## 5. Cách test

### Test endpoint `/v1/images/generations`:
```powershell
$body = @{model="img-gemini-flash"; prompt="A cute cat"} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:5000/v1/images/generations `
  -Method Post `
  -Headers @{Authorization="Bearer subkey_admin_123"; "Content-Type"="application/json"} `
  -Body $body -TimeoutSec 120
```

**Kết quả mong đợi:**
```json
{
  "created": 1770459588,
  "data": [{"url": "http://localhost:5000/v1/_mw/media/<hash>.png"}]
}
```

### Test qua Open WebUI chat:
1. Chọn model `img-gemini-flash`
2. Nhắn prompt tạo ảnh
3. Ảnh hiển thị dạng markdown image (không còn "Chunk too big")

---

## 6. Thông tin kỹ thuật

| Thành phần | Version |
|-----------|---------|
| LiteLLM | 1.81.8 |
| Gemini Flash Image | `gemini-2.5-flash-image` |
| Gemini Pro Image | `gemini-3-pro-image-preview` |
| API Endpoint | `/chat/completions` (qua `generateContent`) |
