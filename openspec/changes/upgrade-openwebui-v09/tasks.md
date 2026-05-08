## Backup (MANDATORY)
- [ ] 1. `pg_dump` PostgreSQL → backup.sql
- [ ] 2. Export custom tools/functions (JSON từ Admin Panel)
- [ ] 3. Backup Dockerfile.openwebui hiện tại

## Sửa Custom Functions (TRƯỚC khi deploy)
- [ ] 4. Sửa Export Excel Tool → async
- [ ] 5. Sửa Export PDF Tool → async
- [ ] 6. Sửa Export Word Tool → async
- [ ] 7. Sửa Timezone Inject Filter → async
- [ ] 8. Test functions trên staging (nếu có)

## Deploy
- [ ] 9. Cập nhật Dockerfile.openwebui: base image → `v0.9.0`
- [ ] 10. `docker compose build open-webui`
- [ ] 11. `docker compose up -d open-webui`
- [ ] 12. Monitor logs: verify Alembic migration
- [ ] 13. Clear browser cache (Ctrl+F5)

## Verification
- [ ] 14. Login/logout
- [ ] 15. Chat completion (all providers)
- [ ] 16. RAG: upload + query
- [ ] 17. Image generation
- [ ] 18. Export Excel/PDF/Word
- [ ] 19. Admin Panel
- [ ] 20. MW Dashboard

## Docs
- [ ] 21. Cập nhật version trong docs
- [ ] 22. Document tính năng mới (Skills, Automations, etc.)

## Rollback (nếu cần)
- [ ] R1. Revert Dockerfile.openwebui
- [ ] R2. `docker compose build open-webui && docker compose up -d open-webui`
- [ ] R3. Restore pg_dump nếu DB migration fail
