# RAG (Retrieval-Augmented Generation) - Kiến trúc chi tiết

> **Hệ thống**: Open WebUI + PostgreSQL + PGVector  
> **Cập nhật**: 2026-02-09

---

## 1. Tổng quan

RAG (Retrieval-Augmented Generation) là kỹ thuật cho phép LLM trả lời dựa trên dữ liệu ngoài (documents, files) thay vì chỉ dựa vào training data. Hệ thống của chúng ta triển khai RAG thông qua Open WebUI tích hợp PGVector.

### 1.1. Luồng hoạt động tổng quát

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INDEXING PHASE                               │
│                                                                     │
│  User Upload File → Extract Text → Split Chunks → Embedding →       │
│  Store in PGVector (document_chunk table)                           │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        RETRIEVAL PHASE                              │
│                                                                     │
│  User Query → Embedding Query → Vector Search (cosine similarity)   │
│  → Top-K Chunks → Inject vào Prompt → LLM Generate Response         │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2. Các thành phần chính

| Thành phần      | Technology                                | Vai trò                                  |
| --------------- | ----------------------------------------- | ---------------------------------------- |
| Vector DB       | PostgreSQL + PGVector 0.8.0               | Lưu trữ và tìm kiếm vector embeddings    |
| Embedding Model | `sentence-transformers/all-MiniLM-L6-v2`  | Chuyển text thành vector 384 chiều       |
| Text Splitter   | Character-based splitter                  | Chia document thành chunks               |
| Search          | Hybrid (BM25 + Vector)                    | Kết hợp keyword search + semantic search |
| Index           | HNSW (Hierarchical Navigable Small World) | Tìm kiếm approximate nearest neighbors   |

---

## 2. Chi tiết kỹ thuật

### 2.1. Cấu hình hiện tại (docker-compose.yml)

```yaml
# RAG Configuration
ENABLE_RAG: true
CHUNK_SIZE: 1000                    # Mỗi chunk tối đa 1000 ký tự
CHUNK_OVERLAP: 200                  # Overlap 200 ký tự giữa các chunks
RAG_TEXT_SPLITTER: character        # Chia theo ký tự (không theo token)
ENABLE_RAG_HYBRID_SEARCH: true      # BM25 + Vector search
RAG_FILE_MAX_SIZE: 10               # Tối đa 10 MB / file
RAG_FILE_MAX_COUNT: 10              # Tối đa 10 files / lần upload

# Embedding
RAG_EMBEDDING_ENGINE: ""            # Local (Sentence Transformers)
RAG_EMBEDDING_MODEL: sentence-transformers/all-MiniLM-L6-v2

# Vector Database
VECTOR_DB: pgvector
PGVECTOR_DB_URL: postgresql://openwebui_user:***@postgres:5432/openwebui
PGVECTOR_CREATE_EXTENSION: true
PGVECTOR_INDEX_METHOD: hnsw
```

### 2.2. Indexing Pipeline (Upload File → Lưu Vector)

#### Bước 1: Extract Text
Open WebUI hỗ trợ nhiều format:
- **PDF**: PyPDF2 / Apache Tika / Docling / Mistral OCR
- **Word** (.docx): python-docx
- **Excel** (.xlsx): openpyxl
- **Text** (.txt, .csv, .md): đọc trực tiếp
- **HTML**: BeautifulSoup

#### Bước 2: Text Splitting (Chunking)

```python
# Character-based splitting (cấu hình hiện tại)
chunk_size = 1000       # Mỗi chunk ≤ 1000 ký tự
chunk_overlap = 200     # Overlap 200 ký tự để giữ context

# Ví dụ: document 3000 ký tự → 4 chunks
# Chunk 1: char 0-999
# Chunk 2: char 800-1799   (overlap 200 từ chunk 1)
# Chunk 3: char 1600-2599  (overlap 200 từ chunk 2)
# Chunk 4: char 2400-2999  (overlap 200 từ chunk 3)
```

**Tại sao overlap?** Để tránh mất context tại ranh giới chunk. Một câu bị cắt giữa chừng sẽ xuất hiện đầy đủ trong chunk kế tiếp.

#### Bước 3: Embedding (Text → Vector)

```
Model: sentence-transformers/all-MiniLM-L6-v2
├── Output dimension: 384 vectors
├── Max input tokens: 256 tokens (~200-300 từ tiếng Anh)
├── Chạy local (không cần API key)
├── Tốc độ: ~500-1000 chunks/giây trên CPU
└── Hỗ trợ: tiếng Anh tốt nhất, tiếng Việt cơ bản
```

> ⚠️ **Lưu ý quan trọng**: Table `document_chunk` hiện cấu hình `vector(1536)` (dimension 1536), nhưng model `all-MiniLM-L6-v2` chỉ output 384 chiều. Open WebUI tự xử lý padding/mapping. Nếu đổi sang OpenAI embeddings (`text-embedding-3-small`) sẽ dùng đúng 1536 chiều.

#### Bước 4: Lưu vào PGVector

Mỗi chunk được lưu vào table `document_chunk`:

```sql
Table "public.document_chunk"
     Column      |     Type     | Nullable
-----------------+--------------+----------
 id              | text         | NOT NULL   -- UUID unique
 vector          | vector(1536) |            -- Vector embedding
 collection_name | text         | NOT NULL   -- Thuộc collection nào
 text            | text         |            -- Nội dung text gốc
 vmetadata       | jsonb        |            -- Metadata (source, page, etc.)

Indexes:
  "document_chunk_pkey" PRIMARY KEY, btree (id)
  "idx_document_chunk_collection_name" btree (collection_name)
  "idx_document_chunk_vector" hnsw (vector vector_cosine_ops)
    WITH (m='16', ef_construction='64')
```

### 2.3. HNSW Index - Giải thích kỹ thuật

HNSW (Hierarchical Navigable Small World) là thuật toán ANN (Approximate Nearest Neighbor) cho phép tìm kiếm vector tương tự rất nhanh.

```
Cấu hình hiện tại:
├── Distance metric: cosine similarity (vector_cosine_ops)
├── m = 16         → Mỗi node kết nối tối đa 16 neighbors
├── ef_construction = 64  → Số candidates khi build index
│
├── Trade-offs:
│   ├── m cao hơn → recall tốt hơn, nhưng tốn RAM + build chậm hơn
│   └── ef_construction cao → build index chậm, nhưng tìm kiếm chính xác hơn
│
└── Hiệu năng:
    ├── Build time: O(N × log(N))
    ├── Search time: O(log(N))  ← RẤT NHANH, kể cả triệu vectors
    └── RAM: ~1.5x kích thước raw vectors
```

### 2.4. Retrieval Pipeline (Query → Relevant Chunks)

#### Hybrid Search (BM25 + Vector)

```
User Query: "Chính sách bảo mật dữ liệu khách hàng"
                │
    ┌───────────┴───────────┐
    │                       │
    ▼                       ▼
BM25 Search             Vector Search
(keyword matching)      (semantic similarity)
    │                       │
    │ Results ranked        │ Results ranked
    │ by term frequency     │ by cosine similarity
    │                       │
    └───────────┬───────────┘
                │
                ▼
        Reciprocal Rank Fusion (RRF)
        (kết hợp 2 ranked lists)
                │
                ▼
        Top-K chunks (mặc định K=4)
                │
                ▼
        Inject vào System Prompt
                │
                ▼
        LLM generates response
        (with citations)
```

**BM25**: Tìm chính xác theo keyword. Tốt cho tên riêng, mã số, thuật ngữ chuyên ngành.  
**Vector Search**: Tìm theo nghĩa (semantic). Tốt cho câu hỏi khái quát, paraphrase.  
**Hybrid**: Kết hợp cả hai → recall tốt nhất.

### 2.5. Prompt Injection

Khi tìm được relevant chunks, Open WebUI inject vào prompt dạng:

```
### Context from uploaded documents:

[Source: document_name.pdf, Page 5]
<nội dung chunk 1>

[Source: document_name.pdf, Page 12]
<nội dung chunk 2>

---
Based on the above context, answer the following question:
<user's question>
```

---

## 3. Cách sử dụng RAG

### 3.1. Tạo Knowledge Collection

1. Vào **Workspace** → **Knowledge** → **Create Knowledge**
2. Đặt tên collection (VD: "Tài liệu nội bộ")
3. Upload files (PDF, DOCX, TXT, CSV, MD, HTML)
4. Chờ hệ thống xử lý (extract → chunk → embed → store)

### 3.2. Sử dụng trong Chat

- **Cách 1**: Attach file trực tiếp trong chat (icon 📎)
- **Cách 2**: Gõ `#` trong chat để chọn Knowledge Collection
- **Cách 3**: Gán Knowledge Collection vào model cụ thể (Admin Settings)

### 3.3. Ví dụ thực tế

```
User: #tài-liệu-nội-bộ Chính sách nghỉ phép của công ty là gì?

System: [Tìm kiếm trong knowledge "tài-liệu-nội-bộ"]
         → Tìm thấy 3 chunks relevant
         → Inject vào prompt

LLM: Theo tài liệu nội bộ (nguồn: HR_Policy.pdf, trang 15),
     chính sách nghỉ phép của công ty bao gồm:
     - Phép năm: 12 ngày/năm
     - Phép ốm: 30 ngày/năm
     [Citation: HR_Policy.pdf]
```

---

## 4. Giới hạn và Khả năng

### 4.1. Giới hạn cấu hình hiện tại

| Thông số                     | Giá trị                 | Ghi chú                                |
| ---------------------------- | ----------------------- | -------------------------------------- |
| File size tối đa             | **10 MB**               | `RAG_FILE_MAX_SIZE=10`                 |
| Số files / lần upload        | **10 files**            | `RAG_FILE_MAX_COUNT=10`                |
| Chunk size                   | 1000 ký tự              | ~150-200 từ tiếng Việt                 |
| Chunk overlap                | 200 ký tự               | ~30-40 từ overlap                      |
| Embedding dimension          | 384 (model) / 1536 (DB) | Model output 384, DB cấp phát 1536     |
| Max input tokens (embedding) | 256 tokens              | Chunk dài hơn sẽ bị truncate khi embed |

### 4.2. Ví dụ: Upload văn bản 100 trang

```
Tình huống: File PDF 100 trang, ~50,000 từ (~250,000 ký tự)

Bước 1. Extract text:
   - 250,000 ký tự extracted
   - Thời gian: 5-30 giây (tùy PDF format, có hình/bảng không)

Bước 2. Chunking:
   - chunk_size = 1000, overlap = 200
   - Số chunks ≈ 250,000 / (1000 - 200) = ~313 chunks

Bước 3. Embedding:
   - 313 chunks × 384 dimensions × 4 bytes = ~480 KB vectors
   - Thời gian: 1-3 giây (CPU local)

Bước 4. Lưu DB:
   - 313 rows trong document_chunk
   - Storage: ~2-5 MB (text + vectors + metadata + indexes)

Kết luận: ✅ HOÀN TOÀN KHẢ THI
Thời gian xử lý: ~30-60 giây tổng cộng
```

### 4.3. Ví dụ: Upload file 100 MB

```
Tình huống: File PDF 100 MB

❌ KHÔNG LOAD ĐƯỢC với cấu hình hiện tại
   - RAG_FILE_MAX_SIZE = 10 MB → bị chặn ngay

Giải pháp nếu muốn xử lý:
1. Tăng RAG_FILE_MAX_SIZE=100 (hoặc lớn hơn)
2. Tăng timeout cho nginx/proxy nếu có
3. Tăng RAM container (embedding chạy local cần RAM)

Ước tính nếu được phép upload:
   - File PDF 100 MB có thể chứa ~500,000-2,000,000 ký tự
   - Số chunks: 2,000,000 / 800 = ~2,500 chunks
   - Embedding time: ~3-10 giây
   - Storage: ~15-30 MB trong DB
   - ✅ Về kỹ thuật khả thi nhưng cần tăng config
```

### 4.4. Giới hạn thực tế và khuyến nghị

| Tình huống      | Khả thi?       | Ghi chú                                  |
| --------------- | -------------- | ---------------------------------------- |
| PDF 10 trang    | ✅ Tốt         | Xử lý < 10 giây                          |
| PDF 100 trang   | ✅ Tốt         | Xử lý < 1 phút                           |
| PDF 500 trang   | ✅ Khả thi     | Xử lý 2-5 phút                           |
| PDF 1000+ trang | ⚠️ Cần monitor | Có thể timeout, cần tăng config          |
| File > 10 MB    | ❌ Bị chặn     | Cần tăng `RAG_FILE_MAX_SIZE`             |
| File > 100 MB   | ⚠️ Cần tuning  | Tăng RAM, timeout, chunk processing      |
| 100 files nhỏ   | ✅ Khả thi     | Upload theo batch 10 files               |
| Tiếng Việt      | ⚠️ Hạn chế     | Model `all-MiniLM-L6-v2` optimize cho EN |

### 4.5. Nâng cấp khuyến nghị cho tiếng Việt

```yaml
# Đổi sang multilingual embedding model
RAG_EMBEDDING_ENGINE: ""
RAG_EMBEDDING_MODEL: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
# → 384 dimensions, hỗ trợ 50+ ngôn ngữ bao gồm tiếng Việt

# Hoặc dùng OpenAI embedding (chính xác hơn nhưng tốn phí)
RAG_EMBEDDING_ENGINE: openai
RAG_EMBEDDING_MODEL: text-embedding-3-small
# → 1536 dimensions, hỗ trợ tiếng Việt tốt
```

---

## 5. Luồng dữ liệu (Data Flow)

```
┌──────────────────────────────────────────────────────────────┐
│                    USER UPLOADS FILE                          │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────┐     ┌──────────────────────┐
│   file table         │     │   document table      │
│   (metadata, path)   │────▶│   (collection_name,   │
│   id, filename,      │     │    title, content)     │
│   meta (JSON)        │     └──────────────────────┘
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐     ┌──────────────────────────────┐
│  knowledge_file      │     │   document_chunk              │
│  (links file to      │     │   id, vector(1536),          │
│   knowledge)         │     │   collection_name,           │
│  knowledge_id,       │     │   text, vmetadata (JSONB)   │
│  file_id             │     │                              │
└──────────────────────┘     │   HNSW Index on vector       │
                             └──────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    USER ASKS QUESTION                         │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│  1. Embed query → vector(384)                                │
│  2. SELECT * FROM document_chunk                             │
│     WHERE collection_name = ?                                │
│     ORDER BY vector <=> query_vector                         │
│     LIMIT 4;                                                 │
│  3. BM25 search trên text column (nếu hybrid search ON)     │
│  4. Merge results (RRF)                                      │
│  5. Inject top-K chunks vào prompt                           │
│  6. LLM generates answer                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. Đầu vào / Đầu ra

### Đầu vào (Input)
- **Files**: PDF, DOCX, TXT, CSV, MD, HTML, Excel
- **Web URLs**: Copy-paste URL, hệ thống fetch + extract
- **YouTube**: Paste URL, extract transcript
- **Raw text**: Paste trực tiếp vào chat

### Đầu ra (Output)
- **Chat response**: LLM trả lời dựa trên context từ documents
- **Citations**: Trích dẫn nguồn (tên file, trang, đoạn text)
- **Relevance scores**: Confidence score cho mỗi retrieved chunk

---

## 7. Security & Access Control

- Mỗi Knowledge Collection có `access_control` (JSON)
- Chỉ owner hoặc user được grant mới truy cập được
- Files được lưu trong Docker volume `openwebui_data`
- Vector data trong PostgreSQL volume `postgres_data`
- Middleware kiểm soát API access qua `SUBKEY_ADMIN`

---

## 8. Tóm tắt kiến trúc

```
             Browser (localhost:3000)
                 │
                 ▼
          ┌─────────────┐
          │  Open WebUI  │────── openwebui_data volume
          │  (port 8080) │       (files, uploads)
          └──────┬──────┘
                 │
        ┌────────┼────────┐
        │        │        │
        ▼        ▼        ▼
  ┌──────────┐ ┌────────┐ ┌───────────┐
  │PostgreSQL│ │Embedding│ │Middleware │
  │+ PGVector│ │ (local) │ │(port 5000)│
  │(port 5432│ │MiniLM-v2│ └─────┬─────┘
  └──────────┘ └────────┘       │
                                ▼
                          ┌──────────┐
                          │ LiteLLM  │
                          │(port 4000)│
                          └──────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              OpenAI API   Gemini API   Other APIs
```
