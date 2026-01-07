# Dashboard Fix - Manual Test Checklist

## Prerequisites
- Services running: `.\scripts\start.ps1`
- Dashboard URL: http://localhost:5000/dashboard (hoặc http://localhost:5000)
- Admin key available in environment

---

## ✅ TEST 1: Login Cookie Persistence
**Mục tiêu:** Verify cookie session works across page refreshes

**Steps:**
1. Open http://localhost:5000
2. Login với admin key
3. ✅ Verify: Status bar shows "Authenticated ✓"
4. ✅ Verify: Metrics load successfully (không còn "Loading...")
5. Refresh trang (F5)
6. ✅ **PASS nếu:** Dashboard tự động vào lại **KHÔNG** yêu cầu nhập admin key
7. ❌ **FAIL nếu:** Quay về màn login

**Expected:** Cookie `mw_admin_session` được gửi kèm mọi request, session tồn tại 4h

---

## ✅ TEST 2: Time Filter không làm mất session
**Mục tiêu:** Filter changes don't trigger re-authentication

**Steps:**
1. Login vào dashboard
2. Click "Last 6h" button
3. ✅ Verify: Data refreshes **KHÔNG** hiện màn login
4. Click "Last 24h"
5. ✅ Verify: Data refreshes bình thường
6. Click custom date range:
   - Select start date (7 days ago)
   - Select end date (today)
   - Click "Apply"
7. ✅ **PASS nếu:** Charts update **KHÔNG** yêu cầu admin key lại
8. ❌ **FAIL nếu:** Bất kỳ filter nào trigger login screen

**Expected:** mwFetch() tự động gửi credentials với mọi request

---

## ✅ TEST 3: 403 Handling (không reload trang)
**Mục tiêu:** Proper 403 handling without page reload loop

**Steps:**
1. Login vào dashboard
2. Open DevTools > Application > Cookies
3. Delete cookie `mw_admin_session`
4. Wait 30s hoặc click time filter button
5. ✅ **PASS nếu:**
   - Status bar shows "Session expired. Please login again."
   - Dashboard switches to login screen **KHÔNG** reload trang
   - Admin key input **VẪN GIỮ** giá trị cũ (nếu có)
6. ❌ **FAIL nếu:**
   - Trang reload liên tục (loop)
   - Input bị clear
   - Console error: "Maximum call stack size exceeded"

**Expected:** stopDashboardLoops() called, showLoginUI() displays, no reload

---

## ✅ TEST 4: EventSource Stream Stability
**Mục tiêu:** SSE connections handle errors gracefully with backoff

**Steps:**
1. Login vào dashboard
2. Scroll to "Recent Events" section
3. ✅ Verify: Events appear (status: ok/pending/reconciled)
4. Open DevTools > Console
5. Stop middleware: `Ctrl+C` in terminal running services
6. ✅ Verify: Status bar shows "Stream disconnected, retry X"
7. ✅ Verify: Event section shows "Stream disconnected. Retrying in Xs..."
8. ✅ Verify: Retry count increases: 1s → 2s → 5s → 10s → 15s max
9. Restart middleware: `.\scripts\start.ps1`
10. ✅ **PASS nếu:** Stream reconnects automatically, status bar updates "Authenticated ✓ (Stream connected)"
11. ❌ **FAIL nếu:** 
    - "Loading..." treo vĩnh viễn
    - Console spam errors continuously
    - No retry backoff

**Expected:** Exponential backoff with max 15s delay, automatic reconnect

---

## ✅ TEST 5: Auth Check Endpoint (Cookie Debug)
**Mục tiêu:** Verify auth_check endpoint works for debugging

**Steps:**
1. Login vào dashboard
2. Open DevTools > Network
3. Dashboard should auto-call `/v1/_mw/auth_check` after login
4. Check response:
   ```json
   {
     "ok": true,
     "ts": "2026-01-07T...",
     "cookie_present": true,
     "auth_method": "cookie",
     "message": "Authentication successful"
   }
   ```
5. ✅ **PASS nếu:** `cookie_present: true` và `auth_method: "cookie"`
6. ❌ **FAIL nếu:** `cookie_present: false` → cookie không được gửi

**Expected:** Status bar shows proper message based on auth_check response

---

## ✅ TEST 6: Host Mismatch Warning (localhost vs 127.0.0.1)
**Mục tiêu:** Dashboard warns about host mismatch causing cookie issues

**Steps:**
1. Login via http://localhost:5000
2. ✅ Verify: auth_check shows `cookie_present: true`
3. Logout
4. Open http://127.0.0.1:5000
5. Login với cùng admin key
6. ✅ Check status bar:
   - Nếu có warning: "Cookie not present - use same host (localhost OR 127.0.0.1, not mixed)"
   - Đây là expected behavior (cookie domain mismatch)
7. ❌ **FAIL nếu:** Không có warning nhưng cookie không work

**Expected:** Dashboard warns users about host consistency

---

## ✅ TEST 7: Access Tab Stream
**Mục tiêu:** Access log stream works independently

**Steps:**
1. Login vào dashboard
2. Click tab "🌐 Access"
3. ✅ Verify: Access summary loads
4. ✅ Verify: Access events stream shows HTTP requests
5. Make some API calls (e.g., curl chat completions)
6. ✅ **PASS nếu:** Access tab shows HTTP logs in real-time
7. Switch back to "📈 Usage" tab
8. ✅ Verify: Usage stream still works

**Expected:** Both streams (audit + access) work independently

---

## ✅ TEST 8: Users Tab (Admin API)
**Mục tiêu:** Users tab loads with RBAC info

**Steps:**
1. Login vào dashboard
2. Click tab "👥 Users"
3. ✅ Verify: User list displays:
   - User ID
   - Role (admin/user)
   - Status (Active/Disabled)
   - Cost Used
   - Limit
   - Allowed Models
4. ✅ **PASS nếu:** Tất cả users hiển thị đúng
5. ❌ **FAIL nếu:** "Loading..." hoặc "Error loading users"

**Expected:** Users tab uses mwFetch() to call `/v1/_mw/admin/users`

---

## ✅ TEST 9: Error State Rendering
**Mục tiêu:** UI shows proper error messages instead of "Loading..."

**Steps:**
1. Login vào dashboard
2. Stop middleware backend
3. Wait 30s for auto-refresh
4. ✅ Verify: Tables show "Error loading data" (NOT "Loading...")
5. ✅ Verify: Status bar shows "Load error: ..."
6. ✅ Verify: Charts don't crash (gracefully skip update)
7. Restart middleware
8. ✅ **PASS nếu:** Dashboard recovers automatically after ~30s
9. ❌ **FAIL nếu:** Dashboard stuck in error state forever

**Expected:** Graceful degradation, clear error messages

---

## ✅ TEST 10: Status Bar Indicators
**Mục tiêu:** Status bar accurately reflects dashboard state

**Steps:**
1. Login → Status: "Authenticated ✓" (green dot)
2. Filter data → Status: "Loading data..." briefly
3. Data loaded → Status: "Authenticated ✓"
4. Delete cookie → Status: "Session expired. Please login again." (red dot, pulsing)
5. Stop middleware → Status: "Stream disconnected, retry X" (yellow dot)
6. ✅ **PASS nếu:** Tất cả states hiển thị đúng
7. ❌ **FAIL nếu:** Status bar không update hoặc sai trạng thái

**Expected:** 
- Green dot: OK
- Yellow dot: Warning (stream issues)
- Red dot (pulsing): Error/expired

---

## 🐛 Common Issues to Watch

### Issue 1: Cookie not sent
**Symptom:** `auth_check` shows `cookie_present: false`  
**Cause:** URL host mismatch (localhost ≠ 127.0.0.1)  
**Fix:** Luôn dùng cùng host (chọn 1 trong 2)

### Issue 2: CORS errors
**Symptom:** Console: "CORS policy blocked"  
**Cause:** Dashboard served from different port  
**Fix:** Verify dashboard is served from same origin as API

### Issue 3: Stream reconnect loop
**Symptom:** Console spam "EventSource error"  
**Fix:** Check backoff logic, should delay exponentially

### Issue 4: Status bar stuck "Loading..."
**Symptom:** Metrics loaded but status bar says "Loading..."  
**Fix:** Ensure updateStatus('ok', 'Authenticated ✓') called after loadSummary()

---

## 📊 Expected Results Summary

| Test | Pass Criteria |
|------|---------------|
| 1. Cookie Persistence | No re-login after F5 |
| 2. Filter Stability | Filter changes don't trigger login |
| 3. 403 Handling | No page reload, clean UI switch |
| 4. Stream Backoff | Exponential retry delays (1s→15s max) |
| 5. Auth Check | `cookie_present: true` |
| 6. Host Warning | Warning shown for localhost≠127.0.0.1 |
| 7. Access Stream | Independent from usage stream |
| 8. Users Tab | Displays RBAC info correctly |
| 9. Error Rendering | Clear error messages, no "Loading..." stuck |
| 10. Status Bar | Accurate state indicators |

---

## 🔧 Debugging Commands

```bash
# Check cookie in browser console
document.cookie

# Test auth_check manually
curl http://localhost:5000/v1/_mw/auth_check -H "Cookie: mw_admin_session=YOUR_SESSION"

# Check middleware logs
tail -f Oppen_Web_UI_fresh/llm-mw/logs/middleware.requests.log
tail -f Oppen_Web_UI_fresh/llm-mw/logs/audit.jsonl

# Test summary endpoint
curl "http://localhost:5000/v1/_mw/summary?minutes=60" -H "Cookie: mw_admin_session=YOUR_SESSION"
```

---

## ✅ Success Criteria

Dashboard fix is **SUCCESSFUL** if:
1. ✅ No reload trang khi filter/refresh (cookie session works)
2. ✅ 403 handling proper (no loop, clean UI switch)
3. ✅ Stream reconnect with backoff (no infinite loading)
4. ✅ Status bar accurate and helpful
5. ✅ All tabs (Usage/Access/Users) work with mwFetch()
6. ✅ Error states render clearly (no stuck "Loading...")

---

**Test Date:** _____________  
**Tester:** _____________  
**Result:** ⬜ PASS / ⬜ FAIL  
**Notes:** ___________________________________
