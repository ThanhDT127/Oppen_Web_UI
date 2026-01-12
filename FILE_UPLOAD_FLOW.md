# LUỒNG XỬ LÝ FILE UPLOAD TRONG HỆ THỐNG

> **Tài liệu này giải thích chi tiết cách OpenWebUI xử lý file uploads (ảnh, documents) và gửi đến LLM models.**

---

## 📋 TÓM TẮT NHANH

**OpenWebUI KHÔNG upload file trực tiếp lên API.** Thay vào đó:

1. **OpenWebUI** đọc file → extract text/convert to base64
2. **Gửi qua API** dưới dạng JSON (text hoặc data URLs)
3. **Middleware** materialize data URLs thành public URLs
4. **LiteLLM** forward đến providers (OpenAI/Gemini)
5. **Providers** xử lý multimodal content

---

## 🔍 CHI TIẾT TỪNG BƯỚC

### **Bước 1: User Upload File trong OpenWebUI**

Khi bạn click vào 📎 icon và chọn file:

```
User Action: Click 📎 → Select file (image.png, document.pdf, etc.)
```

**OpenWebUI xử lý:**

#### **A. Với ảnh (PNG, JPG, WebP, GIF):**
```javascript
// OpenWebUI Frontend (JavaScript)
1. Đọc file bằng FileReader API
2. Convert sang base64
3. Tạo data URL: "data:image/png;base64,iVBORw0KGgoAAAA..."
4. Gửi trong message content
```

**Format gửi đi:**
```json
{
  "model": "gemini-2.0-flash",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Mô tả ảnh này"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAB..."
          }
        }
      ]
    }
  ]
}
```

#### **B. Với documents (PDF, DOCX, TXT):**
```javascript
// OpenWebUI Backend (Python)
1. Đọc file content
2. Extract text (dùng PyPDF2, python-docx, etc.)
3. Gửi dưới dạng plain text trong <source> tags
```

**Format gửi đi:**
```json
{
  "model": "gemini-2.0-flash",
  "messages": [
    {
      "role": "user",
      "content": "### Task: Answer based on context\n<context>\n<source id=\"1\" name=\"document.pdf\">Extracted text from PDF...</source>\n</context>\n\nUser question: Tóm tắt file này?"
    }
  ]
}
```

---

### **Bước 2: Request đến Middleware (Port 5000)**

**Endpoint:** `POST http://localhost:5000/v1/chat/completions`

**Headers:**
```
Authorization: Bearer subkey_admin_123
Content-Type: application/json
```

**Middleware xử lý:**

```python
# File: llm-mw/main.py (line 814-850)

# 1. Validate authentication
user = _require_user(request)

# 2. Parse request body
body = await request.json()
messages = body.get("messages")

# 3. Process multimodal content
for msg in messages:
    content = msg.get("content")
    if isinstance(content, list):
        for item in content:
            # Handle image_url
            if item.get("type") == "image_url":
                image_url_obj = item.get("image_url")
                url = image_url_obj.get("url")
                
                # Nếu là data URL (base64)
                if url.startswith("data:"):
                    # Convert to public URL
                    new_url = _maybe_materialize_data_url(request, url=url)
                    image_url_obj["url"] = new_url
                    # Ví dụ: "http://localhost:5000/v1/_mw/media/abc123.png"

# 4. Forward to LiteLLM
resp = await client.post(
    f"{LITELLM_BASE}/chat/completions",
    headers={"Authorization": f"Bearer {LITELLM_KEY}"},
    json=body
)
```

**Tại sao phải materialize?**
- ❌ **Data URL quá dài:** 1MB image = ~1.37MB base64 string
- ❌ **Provider có thể reject:** OpenAI/Gemini có giới hạn request size
- ✅ **Public URL ngắn hơn:** ~50 bytes thay vì 1.37MB
- ✅ **Cache được:** File lưu local, dùng lại nhiều lần

**Function `_maybe_materialize_data_url()`:**

```python
# File: llm-mw/main.py (line 269-289)

def _maybe_materialize_data_url(request, *, url, fallback_mime="application/octet-stream"):
    if not url.startswith("data:"):
        return url
    
    # Parse: data:image/png;base64,iVBORw0...
    header, b64 = url.split(",", 1)
    mime = fallback_mime
    
    # Extract MIME type
    m = re.match(r"^data:([^;]+);base64$", header)
    if m:
        mime = m.group(1)  # "image/png"
    
    # Decode base64
    raw = base64.b64decode(b64)
    
    # Save to disk: logs/mw_media/abc123.png
    name = _save_bytes_to_media(raw, mime=mime)
    
    # Return public URL
    return _public_media_url(request, name)
    # Result: "http://localhost:5000/v1/_mw/media/abc123.png"
```

**Sau khi materialize:**
```json
{
  "model": "gemini-2.0-flash",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Mô tả ảnh này"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "http://localhost:5000/v1/_mw/media/abc123def456.png"
          }
        }
      ]
    }
  ]
}
```

---

### **Bước 3: Middleware Forward đến LiteLLM (Port 4000)**

**Endpoint:** `POST http://localhost:4000/v1/chat/completions`

**Headers:**
```
Authorization: Bearer super_admin_key_123
Content-Type: application/json
X-Request-ID: mw_abc123
```

**LiteLLM nhận request:**
```python
# LiteLLM xử lý
1. Parse model name: "gemini-2.0-flash"
2. Look up provider: gemini/gemini-2.0-flash
3. Check image URL có accessible không
4. Download image từ URL (nếu cần)
5. Forward đến Gemini API
```

**LiteLLM có thể:**
- ✅ **Download image từ URL** → convert sang format provider cần
- ✅ **Keep URL as-is** nếu provider support public URLs
- ✅ **Convert format** giữa OpenAI format ↔ Gemini format

---

### **Bước 4: LiteLLM Forward đến Provider (Gemini/OpenAI)**

#### **A. Gemini API:**

**Gemini format khác OpenAI:**

```python
# OpenAI format (input):
{
  "type": "image_url",
  "image_url": {"url": "http://..."}
}

# Gemini format (output):
{
  "parts": [
    {"text": "Mô tả ảnh này"},
    {
      "inline_data": {
        "mime_type": "image/png",
        "data": "<base64_string>"
      }
    }
  ]
}
```

**LiteLLM tự động convert:**
1. Download image từ `http://localhost:5000/v1/_mw/media/abc123.png`
2. Convert sang base64
3. Format theo Gemini API spec
4. Gửi đến `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent`

#### **B. OpenAI API:**

**OpenAI format (native):**

```json
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "Describe this image"},
        {
          "type": "image_url",
          "image_url": {
            "url": "http://localhost:5000/v1/_mw/media/abc123.png"
          }
        }
      ]
    }
  ]
}
```

**OpenAI có thể:**
- ✅ **Download image từ URL** (public URLs)
- ✅ **Accept data URLs** (base64 inline)

---

### **Bước 5: Response trở về**

**Provider → LiteLLM → Middleware → OpenWebUI:**

```
Gemini API
  ↓ Response: {"text": "Đây là bức ảnh..."}
LiteLLM
  ↓ Convert to OpenAI format
  ↓ Add usage tokens
Middleware
  ↓ Track usage (tokens, cost)
  ↓ Update users.json
OpenWebUI
  ↓ Display to user
```

**Response format:**
```json
{
  "id": "chatcmpl-abc123",
  "model": "gemini-2.0-flash",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Đây là bức ảnh về phong cảnh núi non..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 1250,
    "completion_tokens": 150,
    "total_tokens": 1400
  },
  "_mw_user": "admin",
  "_mw_added_cost_usd": 0.00175
}
```

---

## 📊 MODELS HỖ TRỢ MULTIMODAL

### **✅ Models hỗ trợ images (vision):**

| Model | Provider | Vision | Documents | Notes |
|-------|----------|--------|-----------|-------|
| **gpt-4o** | OpenAI | ✅ | ✅ (via text extraction) | Best vision model |
| **gpt-4o-mini** | OpenAI | ✅ | ✅ | Cost-effective |
| **gpt-5** | OpenAI | ✅ | ✅ | Reasoning + vision |
| **gemini-2.0-flash** | Google | ✅ | ✅ | Fast, good vision |
| **gemini-2.5-pro** | Google | ✅ | ✅ | Most powerful |
| **gemini-2.5-flash** | Google | ✅ | ✅ | Balanced |

### **❌ Models KHÔNG hỗ trợ images:**

- `gpt-4o-mini-tts` (text-to-speech only)
- `gpt-4o-transcribe` (audio-to-text only)

### **⚠️ Special models:**

- `gemini-2.5-flash-image` - Tối ưu cho image generation (KHÔNG phải vision)

---

## 🎯 CÁCH UPLOAD TRỰC TIẾP LÊN API (Như Chat SaaS)

**Nếu bạn muốn gửi file trực tiếp qua API như ChatGPT/Claude:**

### **Option 1: Base64 inline (OpenWebUI đang dùng)**

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer subkey_admin_123" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "Describe this image"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/png;base64,iVBORw0KGgo..."
            }
          }
        ]
      }
    ]
  }'
```

**✅ Ưu điểm:**
- Không cần upload file riêng
- Một request duy nhất
- OpenWebUI đang dùng cách này

**❌ Nhược điểm:**
- Request size lớn (1MB ảnh = 1.37MB base64)
- Không cache được
- Chậm hơn với file lớn

---

### **Option 2: Public URL (Recommended)**

```bash
# Step 1: Upload file to get URL
curl -X POST http://localhost:5000/v1/_mw/upload \
  -H "Authorization: Bearer subkey_admin_123" \
  -F "file=@image.png"

# Response: {"url": "http://localhost:5000/v1/_mw/media/abc123.png"}

# Step 2: Use URL in chat
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer subkey_admin_123" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "Describe this"},
          {
            "type": "image_url",
            "image_url": {
              "url": "http://localhost:5000/v1/_mw/media/abc123.png"
            }
          }
        ]
      }
    ]
  }'
```

**✅ Ưu điểm:**
- Request nhỏ gọn
- Cache được (dùng lại nhiều lần)
- Nhanh hơn với file lớn

**❌ Nhược điểm:**
- Cần 2 requests
- Phải implement upload endpoint

---

### **Option 3: Multipart Form (Như ChatGPT Web)**

**⚠️ CHƯA IMPLEMENT - Cần thêm code:**

```python
# Thêm vào llm-mw/main.py

@app.post("/v1/chat/completions/multipart")
async def chat_with_files(request: Request):
    """Accept files via multipart/form-data"""
    form = await request.form()
    
    # Parse files
    files = []
    for key in form.keys():
        if key.startswith("file_"):
            file = form[key]
            # Save and get URL
            url = await _save_uploaded_file(file)
            files.append(url)
    
    # Parse JSON body
    body = json.loads(form.get("body"))
    
    # Inject file URLs into messages
    # ...
    
    # Forward to LiteLLM
    # ...
```

**Usage:**
```bash
curl -X POST http://localhost:5000/v1/chat/completions/multipart \
  -H "Authorization: Bearer subkey_admin_123" \
  -F "file_0=@image.png" \
  -F "file_1=@document.pdf" \
  -F 'body={"model":"gpt-4o","messages":[{"role":"user","content":"Analyze these files"}]}'
```

---

## 🔧 HIỆN TRẠNG CODE

### **✅ Đã implement:**

1. **Middleware materialize data URLs** (line 814-850)
   - Xử lý `image_url` type
   - Xử lý generic data URLs
   - Save files to `logs/mw_media/`

2. **Media serving endpoint** (line 319-389)
   - Serve files với correct MIME types
   - Support 30+ file extensions
   - Cache headers (`max-age=31536000`)

3. **MIME type detection** (line 189-246)
   - 30+ file types
   - Images, documents, code, archives

### **❌ Chưa implement:**

1. **Direct file upload endpoint**
   - Không có `/v1/upload` hoặc `/v1/files`
   - Phải gửi base64 qua JSON

2. **Multipart form support**
   - Không có endpoint nhận `multipart/form-data`

3. **File management**
   - Không có list/delete uploaded files
   - Không có cleanup cũ files

---

## 🎬 DEMO FLOW THỰC TẾ

### **Scenario: Upload ảnh và hỏi**

```
┌──────────────┐
│ 1. User      │  Click 📎 → Select cat.png (500KB)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 2. Browser   │  FileReader.readAsDataURL(cat.png)
│   (JS)       │  → "data:image/png;base64,iVBOR..." (685KB string)
└──────┬───────┘
       │
       ▼ POST /v1/chat/completions
┌──────────────┐  Content-Length: 685KB
│ 3. Middleware│  Parse JSON → Find data URL
│   (Python)   │  Decode base64 → Save to disk
│              │  Generate: abc123def456.png (500KB file)
│              │  Replace URL: http://localhost:5000/v1/_mw/media/abc123def456.png
└──────┬───────┘  Content-Length: 2KB (URL thay vì base64)
       │
       ▼ POST /v1/chat/completions
┌──────────────┐  Content-Length: 2KB
│ 4. LiteLLM   │  Parse request → Detect image URL
│              │  HTTP GET http://localhost:5000/v1/_mw/media/abc123def456.png
│              │  Download image (500KB)
│              │  Convert to Gemini format
└──────┬───────┘
       │
       ▼ POST https://generativelanguage.googleapis.com/...
┌──────────────┐
│ 5. Gemini    │  Receive image + text
│   API        │  Process with vision model
│              │  Generate response
└──────┬───────┘
       │
       ▼ JSON response
┌──────────────┐
│ 6. Response  │  LiteLLM → Middleware → OpenWebUI
│   Chain      │  Display: "This is a photo of a cute cat..."
└──────────────┘
```

---

## 📝 KẾT LUẬN

### **OpenWebUI xử lý file như thế nào?**

1. **Images:** Convert to base64 data URLs → Middleware materialize → Forward to LiteLLM
2. **Documents:** Extract text → Gửi as plain text trong context
3. **Không upload trực tiếp:** Tất cả qua JSON API

### **Models nào hỗ trợ multimodal?**

- **OpenAI:** gpt-4o, gpt-4o-mini, gpt-5
- **Gemini:** gemini-2.0-flash, gemini-2.5-pro, gemini-2.5-flash

### **Muốn upload trực tiếp như SaaS?**

**Option hiện tại (đang dùng):**
- ✅ Gửi base64 qua JSON
- ✅ Middleware tự động materialize
- ✅ Không cần thêm code

**Option nâng cao (cần implement):**
- ❌ Upload endpoint riêng (`/v1/upload`)
- ❌ Multipart form support
- ❌ File management (list/delete)

### **Hệ thống đang hoạt động OK?**

✅ **CÓ** - Đang hoạt động đúng như thiết kế:
1. OpenWebUI gửi base64
2. Middleware materialize
3. LiteLLM forward
4. Gemini/OpenAI xử lý
5. Response trở về

**Không cần thay đổi gì** trừ khi bạn muốn thêm tính năng upload riêng!

---

**Last Updated:** December 18, 2025  
**Author:** LLM Middleware System Documentation
