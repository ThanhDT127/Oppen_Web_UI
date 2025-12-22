# REFACTORING PLAN - Middleware Project Structure
**Date:** December 19, 2025  
**Objective:** Reorganize 1553-line main.py into modular, professional structure

---

## 📊 CURRENT STATE ANALYSIS

### File Structure
```
llm-mw/
├── main.py (1552 lines, 56KB) ❌ TOO LARGE
├── users.json
├── prices.json
├── pending.csv
├── migrate_subkeys.py
└── test_new_features.py
```

### main.py Breakdown (by function type)
1. **Configuration & Setup** (lines 1-90): 90 lines
   - Imports, constants, logging setup
   
2. **Utility Functions** (lines 91-470): 380 lines
   - `_env_truthy()`, `_truncate_text()`, `_redact()`, `_safe_headers()`
   - `_detail()`, `_audit_log()` - logging helpers
   - `_mime_to_ext()`, `_save_bytes_to_media()` - media handling
   - `_maybe_materialize_*()` - URL processing
   - `_extract_text_prompt_from_messages()` - message parsing
   
3. **User & Auth Management** (lines 527-730): 203 lines
   - `_hash_subkey()`, `_find_user()`, `_require_user()`
   - `_load_users()`, `_save_users()`
   - `_assert_model_allowed()`
   
4. **Quota & Cost Tracking** (lines 545-710): 165 lines
   - `_get_litellm_cost_from_headers()`
   - `_enforce_and_bump_task_quota()`
   - `_maybe_reset_quota()`, `_period_anchor_ms()`
   - `_calc_cost_usd()`, `_calc_image_cost()`
   
5. **LiteLLM Integration** (lines 790-870): 80 lines
   - `_find_usage_in_litellm_log()` - log parsing
   
6. **FastAPI Endpoints** (lines 471-1553): 1082 lines
   - Startup/shutdown hooks
   - Middleware
   - `/health` - health check
   - `/v1/models` - models list
   - `/v1/chat/completions` - chat
   - `/v1/images/generations` - image gen
   - `/v1/audio/transcriptions` - STT
   - `/v1/_mw/media/{name}` - media serving
   - `/v1/_mw/summary` - analytics
   - `/admin/*` - admin endpoints

---

## 🎯 PROPOSED STRUCTURE

```
llm-mw/
├── main.py                     # FastAPI app & routes only (~300 lines)
├── config.py                   # Configuration & constants
├── requirements.txt
├── migrate_subkeys.py
├── test_new_features.py
│
├── core/                       # Core business logic
│   ├── __init__.py
│   ├── auth.py                 # Authentication & user management
│   ├── quota.py                # Quota tracking & enforcement
│   └── cost.py                 # Cost calculation
│
├── services/                   # External service integrations
│   ├── __init__.py
│   └── litellm.py             # LiteLLM proxy integration
│
├── utils/                      # Utility functions
│   ├── __init__.py
│   ├── logging.py             # Logging helpers (detail, audit)
│   ├── media.py               # Media handling (save, serve, materialize)
│   └── helpers.py             # General helpers (redact, truncate)
│
├── api/                        # API routes (modular endpoints)
│   ├── __init__.py
│   ├── health.py              # Health & monitoring
│   ├── models.py              # Models list
│   ├── chat.py                # Chat completions
│   ├── images.py              # Image generation
│   ├── audio.py               # Audio transcription
│   ├── media.py               # Media serving
│   └── admin.py               # Admin endpoints
│
├── models/                     # Data models (Pydantic)
│   ├── __init__.py
│   ├── user.py                # User model
│   └── quota.py               # Quota model
│
└── data/                       # Data files
    ├── users.json
    ├── prices.json
    └── pending.csv
```

---

## 📋 IMPLEMENTATION PLAN (12 STEPS)

### **PHASE 1: Setup & Preparation** (Steps 1-3)

#### Step 1: Create Directory Structure
**Time:** 2 minutes  
**Risk:** Low  
**Actions:**
- Create all directories: `core/`, `services/`, `utils/`, `api/`, `models/`, `data/`
- Create all `__init__.py` files
- Move data files to `data/` directory

**Files Created:**
- `core/__init__.py`
- `services/__init__.py`
- `utils/__init__.py`
- `api/__init__.py`
- `models/__init__.py`

**Commands:**
```bash
cd D:\Works\Oppen_Web_UI_fresh\llm-mw
mkdir core services utils api models data
move users.json data\
move prices.json data\
move pending.csv data\
```

---

#### Step 2: Extract Configuration
**Time:** 5 minutes  
**Risk:** Low  
**Actions:**
- Create `config.py` with all constants and environment variables
- Keep logging setup in config

**Files Created:**
- `config.py` (~80 lines)

**Extracted from main.py:**
- Lines 1-23: Imports (keep only FastAPI-related in main.py)
- Lines 47-90: Constants, paths, environment variables, logging setup

**Testing:**
```python
from config import LITELLM_BASE, LITELLM_KEY, logger
print(f"✓ Config loaded: {LITELLM_BASE}")
```

---

#### Step 3: Create Data Models
**Time:** 5 minutes  
**Risk:** Low  
**Actions:**
- Create Pydantic models for User and Quota
- Type hints for better IDE support

**Files Created:**
- `models/user.py` (~40 lines)
- `models/quota.py` (~30 lines)

**Benefits:**
- Type safety
- Validation
- Better documentation

---

### **PHASE 2: Extract Utilities** (Steps 4-5)

#### Step 4: Extract Utility Functions
**Time:** 10 minutes  
**Risk:** Low  
**Actions:**
- Create `utils/helpers.py` - general utilities
- Create `utils/logging.py` - logging functions
- Create `utils/media.py` - media handling

**Files Created:**
- `utils/helpers.py` (~100 lines)
  - `_env_truthy()`, `_truncate_text()`, `_redact()`, `_safe_headers()`
  - `_extract_text_prompt_from_messages()`
  
- `utils/logging.py` (~80 lines)
  - `_detail()`, `_audit_log()`
  
- `utils/media.py` (~150 lines)
  - `_mime_to_ext()`, `_save_bytes_to_media()`
  - `_public_media_url()`, `_maybe_materialize_*()` functions

**Testing:**
```python
from utils.helpers import _redact
from utils.logging import _audit_log
from utils.media import _mime_to_ext

# Test each module independently
```

---

#### Step 5: Extract Core Business Logic
**Time:** 15 minutes  
**Risk:** Medium (affects authentication & quota)  
**Actions:**
- Create `core/auth.py` - user management & authentication
- Create `core/quota.py` - quota enforcement
- Create `core/cost.py` - cost calculation

**Files Created:**
- `core/auth.py` (~150 lines)
  - `_hash_subkey()`, `_find_user()`, `_require_user()`
  - `_load_users()`, `_save_users()`
  - `_assert_model_allowed()`
  
- `core/quota.py` (~120 lines)
  - `_enforce_and_bump_task_quota()`
  - `_maybe_reset_quota()`, `_period_anchor_ms()`
  
- `core/cost.py` (~80 lines)
  - `_calc_cost_usd()`, `_calc_image_cost()`
  - Price loading from `data/prices.json`

**Testing:**
```python
from core.auth import _find_user
from core.quota import _enforce_and_bump_task_quota

# Test with existing users.json
```

---

### **PHASE 3: Extract Services** (Step 6)

#### Step 6: Extract LiteLLM Integration
**Time:** 5 minutes  
**Risk:** Low  
**Actions:**
- Create `services/litellm.py` - LiteLLM proxy integration

**Files Created:**
- `services/litellm.py` (~100 lines)
  - `_find_usage_in_litellm_log()`
  - `_get_litellm_cost_from_headers()`

**Testing:**
```python
from services.litellm import _find_usage_in_litellm_log
# Test with sample request_id
```

---

### **PHASE 4: Modularize API Routes** (Steps 7-11)

#### Step 7: Extract Health & Monitoring Routes
**Time:** 5 minutes  
**Risk:** Low  
**Actions:**
- Create `api/health.py` - health check & summary endpoints

**Files Created:**
- `api/health.py` (~150 lines)
  - `GET /health` - enhanced health check
  - `GET /v1/_mw/summary` - usage analytics

**Testing:**
```bash
curl http://localhost:5000/health
curl http://localhost:5000/v1/_mw/summary?minutes=60
```

---

#### Step 8: Extract Models Route
**Time:** 5 minutes  
**Risk:** Low  
**Actions:**
- Create `api/models.py` - models list endpoint

**Files Created:**
- `api/models.py` (~40 lines)
  - `GET /v1/models`

**Testing:**
```bash
curl http://localhost:5000/v1/models -H "Authorization: Bearer subkey_admin_123"
```

---

#### Step 9: Extract Chat Route
**Time:** 10 minutes  
**Risk:** High (most complex endpoint, streaming)  
**Actions:**
- Create `api/chat.py` - chat completions endpoint
- Handle streaming logic carefully

**Files Created:**
- `api/chat.py` (~250 lines)
  - `POST /v1/chat/completions` (streaming & non-streaming)

**Testing:**
```bash
# Non-streaming
curl http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer subkey_admin_123" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"test"}]}'

# Streaming
curl http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer subkey_admin_123" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"test"}],"stream":true}'
```

---

#### Step 10: Extract Images & Audio Routes
**Time:** 10 minutes  
**Risk:** Medium  
**Actions:**
- Create `api/images.py` - image generation
- Create `api/audio.py` - audio transcription
- Create `api/media.py` - media serving

**Files Created:**
- `api/images.py` (~80 lines)
  - `POST /v1/images/generations`
  
- `api/audio.py` (~100 lines)
  - `POST /v1/audio/transcriptions`
  
- `api/media.py` (~40 lines)
  - `GET /v1/_mw/media/{name}`

**Testing:**
```bash
# Image generation
curl http://localhost:5000/v1/images/generations \
  -H "Authorization: Bearer subkey_admin_123" \
  -d '{"model":"gpt-image-1","prompt":"test","n":1}'

# Audio transcription
curl http://localhost:5000/v1/audio/transcriptions \
  -H "Authorization: Bearer subkey_admin_123" \
  -F file=@test.mp3 -F model=gpt-4o-transcribe
```

---

#### Step 11: Extract Admin Routes
**Time:** 5 minutes  
**Risk:** Low  
**Actions:**
- Create `api/admin.py` - admin endpoints

**Files Created:**
- `api/admin.py` (~120 lines)
  - `GET /admin/usage`
  - `POST /admin/reset`
  - `POST /admin/reconcile`

**Testing:**
```bash
curl http://localhost:5000/admin/usage -H "Authorization: Bearer admin_master_key_456"
```

---

### **PHASE 5: Finalize & Test** (Step 12)

#### Step 12: Update main.py & Integration Test
**Time:** 15 minutes  
**Risk:** High (integration issues)  
**Actions:**
- Rewrite `main.py` to import and register all routes
- Update all import paths throughout project
- Run comprehensive test suite
- Update documentation

**New main.py Structure (~200 lines):**
```python
# Imports
from fastapi import FastAPI
from config import *
from api import health, models, chat, images, audio, media, admin

# Create app
app = FastAPI(title="LLM Middleware")

# Register routes
app.include_router(health.router)
app.include_router(models.router)
app.include_router(chat.router)
app.include_router(images.router)
app.include_router(audio.router)
app.include_router(media.router)
app.include_router(admin.router)

# Middleware
@app.middleware("http")
async def _log_requests(request: Request, call_next):
    # ... middleware logic ...

# Startup/shutdown
@app.on_event("startup")
async def _startup():
    # ... startup logic ...

@app.on_event("shutdown")
async def _shutdown():
    # ... shutdown logic ...
```

**Testing:**
1. **Unit Tests:** Test each module independently
2. **Integration Test:** Run full test suite
3. **Manual Test:** Test all endpoints via curl
4. **Load Test:** Verify performance not degraded

**Commands:**
```bash
# Stop services
# ... (close all windows)

# Start with new structure
cd D:\Works\Oppen_Web_UI_fresh
.\START_ALL.bat

# Wait 10 seconds, then test
python llm-mw/test_new_features.py
```

---

## 🎯 SUCCESS CRITERIA

### Must Pass All Tests:
- ✅ Health check returns 200 with all fields
- ✅ Models list returns 18 models
- ✅ Chat completion (streaming & non-streaming)
- ✅ Image generation
- ✅ Audio transcription
- ✅ Admin endpoints work
- ✅ Quota tracking accurate
- ✅ Audit logging writes to audit.jsonl
- ✅ No performance degradation

### Code Quality:
- ✅ All modules < 300 lines
- ✅ Clear separation of concerns
- ✅ Proper type hints
- ✅ Comprehensive docstrings
- ✅ No circular imports

---

## ⚠️ RISKS & MITIGATION

### High Risk Areas:
1. **Import Paths** - Update all relative imports
   - **Mitigation:** Use absolute imports from project root
   
2. **Circular Dependencies** - Core modules importing each other
   - **Mitigation:** Dependency injection, careful planning
   
3. **Streaming Logic** - Chat streaming is complex
   - **Mitigation:** Keep entire streaming logic in one function
   
4. **State Management** - Shared state (users.json, lock)
   - **Mitigation:** Keep state management in core/auth.py

### Medium Risk Areas:
1. **File Paths** - users.json, prices.json moved to data/
   - **Mitigation:** Update all references, test file operations
   
2. **Quota Logic** - Complex quota enforcement
   - **Mitigation:** Keep quota logic together in core/quota.py

---

## 📦 ROLLBACK PLAN

If refactoring fails:
1. **Backup:** Create `main.py.backup` before starting
2. **Git:** Commit after each phase
3. **Restore:** Copy backup back if needed

```bash
# Before starting
cd D:\Works\Oppen_Web_UI_fresh\llm-mw
copy main.py main.py.backup
```

---

## 📊 ESTIMATED TIMELINE

| Phase | Steps | Time | Risk |
|-------|-------|------|------|
| Phase 1 | 1-3 | 15 min | Low |
| Phase 2 | 4-5 | 25 min | Medium |
| Phase 3 | 6 | 5 min | Low |
| Phase 4 | 7-11 | 35 min | High |
| Phase 5 | 12 | 15 min | High |
| **Total** | **12 steps** | **95 min** | - |

**Buffer:** +30 min for debugging  
**Grand Total:** ~2 hours

---

## 🚀 READY TO START?

Reply với:
- **"start"** - Bắt đầu từ Step 1
- **"review"** - Xem lại plan trước khi bắt đầu
- **"modify"** - Điều chỉnh plan

**Recommended:** Backup main.py trước khi bắt đầu!
