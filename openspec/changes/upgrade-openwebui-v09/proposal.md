# Upgrade Open WebUI → v0.9.0

## Lý do

- v0.9 (Apr 2026): Full async backend, Native Desktop app, Automations/Calendar, Skills system stable
- v0.8 (Feb 2026): Analytics Dashboard, Message Queuing, Python Sandbox
- Hiện tại dùng `open-webui:main` (tracking latest ~v0.8.x)

## ⚠️ Breaking Changes

### Backend Async Migration

v0.9 chuyển toàn bộ backend từ sync → async. **TẤT CẢ custom Functions/Tools phải sửa.**

| Component | Hiện tại | Sau upgrade | Cần làm |
|-----------|---------|-------------|---------|
| Export Excel Tool | `def action(...)` | `async def action(...)` | Sửa code |
| Export PDF Tool | `def action(...)` | `async def action(...)` | Sửa code |
| Export Word Tool | `def action(...)` | `async def action(...)` | Sửa code |
| Timezone Filter | `def inlet(...)` | `async def inlet(...)` | Sửa code |
| DB model methods | `Users.get_user_by_id()` | `await Users.get_user_by_id()` | Thêm await |

### Không ảnh hưởng

| Component | Lý do |
|-----------|-------|
| Middleware container | Container riêng, không phụ thuộc Open WebUI code |
| LiteLLM container | Container riêng |
| Nginx | Routing config không đổi |
| PostgreSQL data | Auto-migrate bởi Alembic |
| Knowledge Base / RAG | PGVector data preserved |
| Chat history | Auto-migrate |
| User accounts | Auto-migrate |

## Scope

### [MODIFY] [Dockerfile.openwebui](file:///C:/Code/openwebui_fetch/Oppen_Web_UI/Dockerfile.openwebui)
- Base image: `open-webui:main` → `open-webui:v0.9.0`
- Verify pip dependencies vẫn compatible

### [MODIFY] Custom Functions/Tools
- Export Excel: sync → async
- Export PDF: sync → async
- Export Word: sync → async
- Timezone inject filter: sync → async
- Tất cả DB calls → thêm `await`

### [MODIFY] Docs
- Cập nhật version, tính năng mới, migration notes

## Quy trình Deploy

```
1. pg_dump backup PostgreSQL
2. Export custom tools/functions (JSON backup)
3. Sửa custom functions → async
4. Update Dockerfile.openwebui base image
5. docker compose build open-webui
6. docker compose up -d open-webui (chỉ restart OW, giữ nguyên containers khác)
7. Monitor logs: verify Alembic migration success
8. Test: chat, RAG, image gen, export tools
9. Rollback plan: revert Dockerfile + docker compose up -d
```

## Rủi ro

> [!CAUTION]
> - Custom Functions **SẼ BREAK** nếu không sửa async
> - Multi-worker rolling update **KHÔNG hỗ trợ** (tất cả workers phải update cùng lúc)
> - Open WebUI built-in Analytics Dashboard có thể **trùng** với MW Dashboard → cần quyết định dùng cái nào

## Prerequisites

- Tất cả 3 changes khác nên hoàn thành trước
- Backup PostgreSQL mandatory
- Custom functions phải được sửa + test trước khi deploy

## Verification

- [ ] Login/logout hoạt động
- [ ] Chat completion qua tất cả providers
- [ ] RAG: upload file, query knowledge base
- [ ] Image generation
- [ ] Export Excel/PDF/Word tools
- [ ] Timezone filter inject
- [ ] Admin Panel accessible
- [ ] MW Dashboard vẫn hoạt động
