## Context

Middleware (`llm-mw`) quản lý users qua pattern `load_users()` / `save_users()` trong `core/auth.py`. Pattern này load toàn bộ users từ DB (hoặc JSON fallback) vào memory, tìm user bằng loop, rồi ghi lại toàn bộ list. Với ~10 users hiện tại, latency không đáng kể. Với 200 users mục tiêu, mỗi chat message sẽ gây 4 full-table scans, ~800 loop iterations, và 3 full-table UPSERT operations.

Kiến trúc hiện tại:
- DB pool: `ThreadedConnectionPool(min=5, max=30)` — psycopg2
- Table: `mw_users` — PostgreSQL, có `user_id` column (PRIMARY KEY)
- Auth pattern: `load_users()` → linear search → `save_users(users)` — ghi toàn bộ list
- Thread safety: `threading.Lock` global — serialize tất cả write operations

Hot path (mỗi chat request): `require_user()` → `enforce_and_bump_quota()` → `_finalize_streaming()` → `check_and_send_alerts()`

## Goals / Non-Goals

**Goals:**
- Giảm query overhead từ O(N) xuống O(1) cho single-user operations
- Thay thế load-all → modify → save-all bằng atomic UPDATE per user
- Giữ backward compatibility với HTTP API (không đổi external contract)
- Giữ lại `load_users()` cho use cases cần full list (dashboard, bulk export)
- Giữ file-based JSON backup mechanism (dual-write to DB + file)

**Non-Goals:**
- Không thay đổi DB schema (table `mw_users` giữ nguyên)
- Không refactor authentication flow (HMAC-SHA256 subkey matching giữ nguyên)
- Không thêm caching layer (Redis) — đó là Phase riêng
- Không thay đổi thread lock strategy — giữ `threading.Lock` cho atomic quota operations

## Decisions

### Decision 1: Thêm `get_user_by_id()` thay vì caching

**Chọn**: Direct indexed query `SELECT ... WHERE user_id = %s`

**Lý do**: 
- `user_id` đã là PRIMARY KEY → indexed lookup O(1)
- Không cần thêm complexity của cache invalidation
- Latency của indexed PG query trên localhost: <1ms
- Đơn giản, dễ test, không thêm dependency

**Alternatives xem xét**:
- In-memory dict cache + TTL → Phức tạp hơn, risk stale data, cross-worker sync
- Redis cache → Thêm dependency, overkill cho use case này

### Decision 2: Atomic field update thay vì load-modify-save

**Chọn**: `UPDATE mw_users SET used_cost_usd = used_cost_usd + %s WHERE user_id = %s`

**Lý do**:
- SQL atomic increment không cần application-level lock cho numeric fields
- Giảm write amplification từ 200 rows → 1 row
- Thread-safe intrinsically (PostgreSQL row-level lock)
- Vẫn giữ JSON file backup bằng cách chỉ update 1 entry trong file

**Alternatives xem xét**:
- Keep load-modify-save nhưng chỉ save changed user → Vẫn cần load all, chỉ giảm write
- UPSERT single user → Tốt nhưng cần serialize JSON fields (quota, alerts_sent)

### Decision 3: Dual-path — giữ `load_users()` cho admin path

**Chọn**: Thêm hàm mới, không xóa hàm cũ

**Lý do**:
- Admin endpoints (list all users, dashboard) vẫn cần full list
- Migration incremental — sửa hot path trước, admin path sau
- Không breaking cho code chưa migrate

### Decision 4: JSON backup strategy cho single-user update

**Chọn**: Read JSON file → update 1 entry → write JSON file

**Lý do**:
- JSON file là backup, không cần atomic
- File nhỏ (200 users ≈ 50KB JSON), I/O nhanh
- Giữ consistency với dual-write pattern hiện tại

## Risks / Trade-offs

- **[Risk] Quota race condition khi bỏ global lock cho atomic UPDATE** → Mitigation: PostgreSQL row-level lock đủ cho numeric increment. Giữ threading.Lock cho complex multi-field operations (reset quota period cần read-then-write nhiều fields)
- **[Risk] JSON file backup có thể stale nếu crash giữa DB update và file write** → Mitigation: Acceptable — DB là primary, file là backup. Hiện tại cũng có risk tương tự
- **[Risk] `save_users_file()` với partial update phức tạp hơn** → Mitigation: Helper function `_update_user_in_file(user_id, updates)` đọc → sửa 1 entry → ghi
- **[Risk] Admin path vẫn dùng load_users() cũ — inconsistent** → Mitigation: Phase 2 refactor admin, không block Phase 0

## Migration Plan

1. Thêm hàm mới vào `core/auth.py` + `core/db.py` (non-breaking)
2. Sửa hot-path files 1 file tại 1 thời điểm, test sau mỗi lần
3. Sửa admin-path files
4. Update `test_alerting.py`
5. Run full test suite + benchmark 200 simulated users
6. Rollback: Revert commits — hàm cũ vẫn tồn tại, không xóa
