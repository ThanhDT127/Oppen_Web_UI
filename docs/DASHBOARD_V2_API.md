# Dashboard v2 API Documentation

## Enhanced Summary Endpoint

### GET /v1/_mw/summary

Enhanced endpoint with time range, breakdown, and timeseries support.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `minutes` | int | 60 | Time window in minutes (legacy, fallback) |
| `start` | string | null | ISO datetime start (e.g., "2026-01-07T00:00:00+07:00") |
| `end` | string | null | ISO datetime end |
| `bucket` | string | "auto" | Timeseries bucket size: "auto", "minute", "hour", "day" |

**When to use:**
- Use `start` + `end` for custom ranges (e.g., last 7 days, specific date)
- Use `minutes` for quick ranges (e.g., last 1 hour)
- `bucket` auto-determines granularity:
  - <= 1 hour → minute buckets
  - <= 2 days → hour buckets
  - \> 2 days → day buckets

**Response Structure:**

```json
{
  "time_range": {
    "start": "2026-01-07T00:00:00+00:00",
    "end": "2026-01-07T23:59:59+00:00",
    "bucket_size": "hour"
  },
  "totals": {
    "requests_total": 150,         // ⚠️ RID-distinct count (control-grade)
    "requests_ok": 145,
    "pending_open_count": 2,       // Last status per RID = "pending"
    "error_count": 3,
    "error_rate_percent": 2.0,
    "tokens_total": 125000,
    "cost_total_usd": 0.1234,
    "p95_latency_ms": 1234.56,
    "chat_calls": 120,
    "image_calls": 25,
    "audio_calls": 5,
    "video_calls": 0
  },
  "breakdown_by_user": [
    {
      "user_id": "admin",
      "requests_total": 100,      // RID-distinct
      "requests_ok": 98,
      "errors": 2,
      "error_rate_percent": 2.0,
      "tokens_total": 90000,
      "cost_usd": 0.0987,
      "p95_latency_ms": 1200.0
    }
  ],
  "breakdown_by_model": [
    {
      "model": "gemini-2.5-flash",
      "requests_total": 80,       // RID-distinct
      "requests_ok": 78,
      "errors": 2,
      "error_rate_percent": 2.5,
      "tokens_total": 70000,
      "cost_usd": 0.0654,
      "p95_latency_ms": 1150.0
    }
  ],
  "timeseries": [
    {
      "ts": "2026-01-07T00:00:00",
      "requests_total": 12,       // RID-distinct in this bucket
      "tokens_total": 10000,
      "cost_usd": 0.0098,
      "errors": 0
    },
    {
      "ts": "2026-01-07T01:00:00",
      "requests_total": 15,
      "tokens_total": 12000,
      "cost_usd": 0.0112,
      "errors": 1
    }
  ]
}
```

**Key Features:**

1. **RID-Distinct Counting (Control-Grade):**
   - All `requests_total` counts are based on unique RIDs
   - For streaming: pending + reconciled = 1 request (not 2)
   - Prevents double-counting in metrics

2. **Last Status Per RID:**
   - `pending_open_count`: Count of RIDs where last_status == "pending"
   - Reflects true open pending requests, not all pending events

3. **Timeseries Aggregation:**
   - Buckets aggregated by time
   - Each RID counted once per bucket (based on first event in bucket)
   - Tokens/cost from final status only (ok/reconciled)

4. **Rotated Log Support:**
   - Reads up to 10 rotated audit.jsonl files
   - Enables historical queries (7d, 30d)

**Examples:**

```bash
# Last hour (minute buckets)
curl "http://localhost:5000/v1/_mw/summary?minutes=60&bucket=minute" \
  -H "X-Admin-Key: $ADMIN_KEY"

# Last 7 days (day buckets)
START=$(date -u -d '7 days ago' +%Y-%m-%dT00:00:00Z)
END=$(date -u +%Y-%m-%dT23:59:59Z)
curl "http://localhost:5000/v1/_mw/summary?start=$START&end=$END&bucket=day" \
  -H "X-Admin-Key: $ADMIN_KEY"

# Custom range with auto bucket
curl "http://localhost:5000/v1/_mw/summary?start=2026-01-01T00:00:00Z&end=2026-01-07T23:59:59Z" \
  -H "X-Admin-Key: $ADMIN_KEY"
```

---

## Access Log Endpoints

### GET /v1/_mw/access_summary

Aggregate HTTP access logs (separate from usage audit).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `minutes` | int | 60 | Time window in minutes |
| `start` | string | null | ISO datetime start |
| `end` | string | null | ISO datetime end |

**Response:**

```json
{
  "time_range": {
    "start": "2026-01-07T10:00:00+00:00",
    "end": "2026-01-07T11:00:00+00:00"
  },
  "totals": {
    "requests_total": 1200,
    "error_count": 15,
    "error_rate_percent": 1.25,
    "avg_latency_ms": 45.67,
    "p95_latency_ms": 123.45
  },
  "breakdown_by_path": [
    {"path": "/v1/chat/completions", "count": 800},
    {"path": "/v1/_mw/summary", "count": 250},
    {"path": "/health", "count": 100}
  ],
  "breakdown_by_status": [
    {"status": 200, "count": 1150},
    {"status": 403, "count": 10},
    {"status": 500, "count": 5}
  ],
  "breakdown_by_method": [
    {"method": "POST", "count": 900},
    {"method": "GET", "count": 300}
  ]
}
```

**Purpose:**
- Monitor HTTP access patterns
- Separate from LLM usage metrics
- Includes dashboard polling (no noise in usage metrics)

---

### GET /v1/_mw/access_stream

SSE stream for realtime access log events.

**Response Format:** Server-Sent Events

```
event: access
data: {"ts":"2026-01-07T10:15:30Z","event":"outbound","path":"/v1/chat/completions","method":"POST","status":200,"ms":123.4}

event: access
data: {"ts":"2026-01-07T10:15:31Z","event":"outbound","path":"/v1/_mw/summary","method":"GET","status":200,"ms":5.6}
```

**Features:**
- Tails `logs/middleware.requests.log`
- Rotation detection (file shrink → reset + reread)
- Keepalive pings every 30s

---

## Differences: Usage vs Access

| Aspect | Usage Audit | Access Log |
|--------|-------------|------------|
| **Source** | `logs/audit.jsonl` | `logs/middleware.requests.log` |
| **Purpose** | LLM usage tracking (cost/tokens/quota) | HTTP access monitoring |
| **Events** | One per LLM request (final status) | All HTTP requests |
| **Includes** | Chat, images, audio completions | Everything (health, summary, dashboard) |
| **Metrics** | Tokens, cost, model, user_id | HTTP status, path, latency |
| **Endpoint** | `/v1/_mw/summary` | `/v1/_mw/access_summary` |
| **Stream** | `/v1/_mw/stream` | `/v1/_mw/access_stream` |

**Why Separate?**
- Dashboard polling creates noise in usage metrics
- Access logs include non-LLM requests (health checks, admin endpoints)
- Clean separation for different monitoring needs

---

## Testing

### Test Summary with Time Range

```bash
# Test 24-hour range
curl "http://localhost:5000/v1/_mw/summary?start=2026-01-06T00:00:00Z&end=2026-01-07T00:00:00Z&bucket=hour" \
  -H "X-Admin-Key: $ADMIN_KEY" | jq .

# Verify:
# - timeseries has 24 entries (hour buckets)
# - requests_total is RID-distinct
# - pending_open_count reflects last status per RID
```

### Test Access Summary

```bash
# Test access logs
curl "http://localhost:5000/v1/_mw/access_summary?minutes=60" \
  -H "X-Admin-Key: $ADMIN_KEY" | jq .

# Verify:
# - breakdown_by_path includes /v1/_mw/summary (dashboard polling)
# - totals.requests_total includes all HTTP requests
```

### Test SSE Streams

```bash
# Test audit stream
curl -N "http://localhost:5000/v1/_mw/stream" \
  -H "X-Admin-Key: $ADMIN_KEY"

# Test access stream
curl -N "http://localhost:5000/v1/_mw/access_stream" \
  -H "X-Admin-Key: $ADMIN_KEY"

# Generate events by making requests in another terminal
curl "http://localhost:5000/v1/chat/completions" \
  -H "Authorization: Bearer subkey_admin_123" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"test"}]}'
```

---

## Migration Notes

### For Existing Dashboards

Old endpoint still works but is legacy:
```bash
# Old way (minutes only)
GET /v1/_mw/summary?minutes=60

# New way (same result, but with enhanced features)
GET /v1/_mw/summary?minutes=60
```

The old `minutes` parameter is preserved for backward compatibility.

### Dashboard Updates Needed

If updating dashboard UI:
1. Replace `/v1/_mw/summary` calls with time range params
2. Add tabs for Usage vs Access
3. Use timeseries data for charts
4. Show breakdown tables for top users/models

---

## Performance Notes

### Large Time Ranges

- 7-day ranges: Reads ~7 rotated files (~350MB)
- 30-day ranges: May timeout if audit log is very large
- **Recommendation:** Use appropriate bucket sizes:
  - 1 hour: `bucket=minute`
  - 24 hours: `bucket=hour`
  - 7-30 days: `bucket=day`

### Caching

Currently no caching. Future improvements:
- Redis cache for timeseries buckets
- Pre-aggregated daily summaries
- Incremental updates instead of full scans

### Optimization Tips

1. Use smaller time ranges when possible
2. Rely on `bucket=day` for historical analysis
3. Poll summary less frequently (5-10s instead of 1s)
4. Use SSE streams for realtime updates
