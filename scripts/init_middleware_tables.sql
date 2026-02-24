-- =============================================================================
-- MIDDLEWARE LOGGING & USAGE TABLES
-- Thêm vào PostgreSQL để lưu trữ logging, quota, usage thay vì JSON files
-- =============================================================================

-- 1. Bảng người dùng middleware (thay thế users.json)
CREATE TABLE IF NOT EXISTS mw_users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) UNIQUE NOT NULL,
    subkey VARCHAR(200) UNIQUE NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    allowed_models TEXT[] DEFAULT ARRAY['*'],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index cho lookup nhanh
CREATE INDEX IF NOT EXISTS idx_mw_users_subkey ON mw_users(subkey);

-- 2. Bảng quota settings cho mỗi user
CREATE TABLE IF NOT EXISTS mw_user_quotas (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) REFERENCES mw_users(user_id) ON DELETE CASCADE,
    period VARCHAR(20) DEFAULT 'monthly',          -- weekly, monthly
    timezone VARCHAR(50) DEFAULT 'Asia/Bangkok',
    period_start BIGINT DEFAULT 0,                 -- timestamp ms
    
    -- Limits
    limit_tokens BIGINT DEFAULT 0,                 -- 0 = unlimited
    limit_cost_usd NUMERIC(12,6) DEFAULT 0,
    limit_image_requests INTEGER DEFAULT 0,
    limit_tts_requests INTEGER DEFAULT 0,
    limit_tts_chars BIGINT DEFAULT 0,
    limit_stt_requests INTEGER DEFAULT 0,
    limit_video_requests INTEGER DEFAULT 0,
    limit_video_seconds NUMERIC(12,2) DEFAULT 0,
    
    -- Usage counters (reset mỗi period)
    used_tokens BIGINT DEFAULT 0,
    used_cost_usd NUMERIC(12,6) DEFAULT 0,
    used_image_requests INTEGER DEFAULT 0,
    used_tts_requests INTEGER DEFAULT 0,
    used_tts_chars BIGINT DEFAULT 0,
    used_stt_requests INTEGER DEFAULT 0,
    used_video_requests INTEGER DEFAULT 0,
    used_video_seconds NUMERIC(12,2) DEFAULT 0,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- 3. Bảng log requests (thay thế middleware.log)
CREATE TABLE IF NOT EXISTS mw_request_logs (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(100) UNIQUE NOT NULL,       -- mw_uuid
    user_id VARCHAR(100) NOT NULL,
    
    -- Request info
    endpoint VARCHAR(100) NOT NULL,                -- /v1/chat/completions, /v1/images/generations...
    method VARCHAR(10) NOT NULL,
    model VARCHAR(100),
    
    -- Response info
    status_code INTEGER,
    latency_ms NUMERIC(12,2),
    
    -- Usage
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    
    -- Cost tracking
    cost_usd NUMERIC(12,6) DEFAULT 0,
    cost_source VARCHAR(20),                       -- 'litellm_header', 'fallback_prices'
    
    -- Streaming info
    is_streaming BOOLEAN DEFAULT FALSE,
    stream_completed BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    request_body JSONB,                            -- Optional: lưu request body
    response_summary JSONB,                        -- Optional: lưu summary response
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes cho query performance
CREATE INDEX IF NOT EXISTS idx_mw_request_logs_user_id ON mw_request_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_mw_request_logs_created_at ON mw_request_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_mw_request_logs_endpoint ON mw_request_logs(endpoint);
CREATE INDEX IF NOT EXISTS idx_mw_request_logs_model ON mw_request_logs(model);

-- 4. Bảng tổng hợp usage theo ngày (cho dashboard/reports)
CREATE TABLE IF NOT EXISTS mw_daily_usage (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    
    -- Aggregated counters
    total_requests INTEGER DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    total_prompt_tokens BIGINT DEFAULT 0,
    total_completion_tokens BIGINT DEFAULT 0,
    total_cost_usd NUMERIC(12,6) DEFAULT 0,
    
    -- By endpoint type
    chat_requests INTEGER DEFAULT 0,
    image_requests INTEGER DEFAULT 0,
    tts_requests INTEGER DEFAULT 0,
    stt_requests INTEGER DEFAULT 0,
    video_requests INTEGER DEFAULT 0,
    
    -- By model (JSONB for flexibility)
    usage_by_model JSONB DEFAULT '{}',
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_mw_daily_usage_date ON mw_daily_usage(date);
CREATE INDEX IF NOT EXISTS idx_mw_daily_usage_user_date ON mw_daily_usage(user_id, date);

-- 5. Bảng giá (thay thế prices.json) - Optional
CREATE TABLE IF NOT EXISTS mw_model_prices (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) UNIQUE NOT NULL,
    provider VARCHAR(50),                          -- openai, google, anthropic...
    
    -- Text/Chat pricing
    input_per_1m NUMERIC(12,6),                    -- USD per 1M tokens
    output_per_1m NUMERIC(12,6),
    
    -- Image pricing
    per_image_usd_low NUMERIC(12,6),
    per_image_usd_medium NUMERIC(12,6),
    per_image_usd_high NUMERIC(12,6),
    
    -- Audio pricing
    tts_usd_per_1m_chars NUMERIC(12,6),
    stt_usd_per_minute NUMERIC(12,6),
    
    -- Video pricing
    video_usd_per_second NUMERIC(12,6),
    
    notes TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Bảng pending requests (thay thế pending.csv)
CREATE TABLE IF NOT EXISTS mw_pending_requests (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    endpoint VARCHAR(100),
    model VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- VIEWS cho Dashboard/Reports
-- =============================================================================

-- View: Tổng hợp usage theo user
CREATE OR REPLACE VIEW vw_user_usage_summary AS
SELECT 
    u.user_id,
    u.active,
    q.period,
    q.limit_tokens,
    q.used_tokens,
    CASE WHEN q.limit_tokens > 0 
         THEN ROUND((q.used_tokens::numeric / q.limit_tokens) * 100, 2) 
         ELSE 0 END as tokens_usage_percent,
    q.limit_cost_usd,
    q.used_cost_usd,
    CASE WHEN q.limit_cost_usd > 0 
         THEN ROUND((q.used_cost_usd / q.limit_cost_usd) * 100, 2) 
         ELSE 0 END as cost_usage_percent,
    q.used_image_requests,
    q.used_tts_requests,
    q.used_stt_requests,
    q.used_video_requests
FROM mw_users u
LEFT JOIN mw_user_quotas q ON u.user_id = q.user_id;

-- View: Requests trong 24h gần nhất
CREATE OR REPLACE VIEW vw_recent_requests AS
SELECT 
    request_id,
    user_id,
    endpoint,
    model,
    status_code,
    latency_ms,
    total_tokens,
    cost_usd,
    is_streaming,
    created_at
FROM mw_request_logs
WHERE created_at >= NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;

-- View: Usage theo ngày (7 ngày gần nhất)
CREATE OR REPLACE VIEW vw_weekly_usage AS
SELECT 
    date,
    SUM(total_requests) as total_requests,
    SUM(total_tokens) as total_tokens,
    SUM(total_cost_usd) as total_cost_usd,
    SUM(chat_requests) as chat_requests,
    SUM(image_requests) as image_requests,
    SUM(tts_requests) as tts_requests
FROM mw_daily_usage
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY date
ORDER BY date DESC;

-- =============================================================================
-- FUNCTIONS cho Middleware integration
-- =============================================================================

-- Function: Log request và update quota atomic
CREATE OR REPLACE FUNCTION fn_log_request_and_update_quota(
    p_request_id VARCHAR,
    p_user_id VARCHAR,
    p_endpoint VARCHAR,
    p_method VARCHAR,
    p_model VARCHAR,
    p_status_code INTEGER,
    p_latency_ms NUMERIC,
    p_prompt_tokens INTEGER,
    p_completion_tokens INTEGER,
    p_cost_usd NUMERIC,
    p_cost_source VARCHAR,
    p_is_streaming BOOLEAN
) RETURNS void AS $$
BEGIN
    -- Insert request log
    INSERT INTO mw_request_logs (
        request_id, user_id, endpoint, method, model,
        status_code, latency_ms,
        prompt_tokens, completion_tokens, total_tokens,
        cost_usd, cost_source, is_streaming
    ) VALUES (
        p_request_id, p_user_id, p_endpoint, p_method, p_model,
        p_status_code, p_latency_ms,
        p_prompt_tokens, p_completion_tokens, p_prompt_tokens + p_completion_tokens,
        p_cost_usd, p_cost_source, p_is_streaming
    );
    
    -- Update quota
    UPDATE mw_user_quotas SET
        used_tokens = used_tokens + p_prompt_tokens + p_completion_tokens,
        used_cost_usd = used_cost_usd + p_cost_usd,
        updated_at = CURRENT_TIMESTAMP
    WHERE user_id = p_user_id;
    
    -- Update daily usage
    INSERT INTO mw_daily_usage (user_id, date, total_requests, total_tokens, total_cost_usd, chat_requests)
    VALUES (p_user_id, CURRENT_DATE, 1, p_prompt_tokens + p_completion_tokens, p_cost_usd, 
            CASE WHEN p_endpoint LIKE '%chat%' THEN 1 ELSE 0 END)
    ON CONFLICT (user_id, date) DO UPDATE SET
        total_requests = mw_daily_usage.total_requests + 1,
        total_tokens = mw_daily_usage.total_tokens + p_prompt_tokens + p_completion_tokens,
        total_cost_usd = mw_daily_usage.total_cost_usd + p_cost_usd,
        chat_requests = mw_daily_usage.chat_requests + CASE WHEN p_endpoint LIKE '%chat%' THEN 1 ELSE 0 END,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Function: Reset quota theo period
CREATE OR REPLACE FUNCTION fn_reset_user_quota(p_user_id VARCHAR) RETURNS void AS $$
BEGIN
    UPDATE mw_user_quotas SET
        period_start = EXTRACT(EPOCH FROM NOW()) * 1000,
        used_tokens = 0,
        used_cost_usd = 0,
        used_image_requests = 0,
        used_tts_requests = 0,
        used_tts_chars = 0,
        used_stt_requests = 0,
        used_video_requests = 0,
        used_video_seconds = 0,
        updated_at = CURRENT_TIMESTAMP
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- SAMPLE DATA (migrate từ users.json)
-- =============================================================================

-- Insert admin user
INSERT INTO mw_users (user_id, subkey, active, allowed_models)
VALUES ('admin', 'subkey_admin_123', true, ARRAY['*'])
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO mw_user_quotas (user_id, period, timezone, limit_tokens, limit_cost_usd)
VALUES ('admin', 'monthly', 'Asia/Bangkok', 0, 0)
ON CONFLICT (user_id) DO NOTHING;

-- Insert sample users
INSERT INTO mw_users (user_id, subkey, active, allowed_models)
VALUES 
    ('user1', 'subkey_user1_abc', true, ARRAY['*']),
    ('user2', 'subkey_user2_xyz', true, ARRAY['*'])
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO mw_user_quotas (user_id, period, timezone, limit_tokens, limit_cost_usd)
VALUES 
    ('user1', 'weekly', 'Asia/Bangkok', 200000, 10.0),
    ('user2', 'monthly', 'Asia/Bangkok', 50000, 25.0)
ON CONFLICT (user_id) DO NOTHING;

-- =============================================================================
-- COMMENTS
-- =============================================================================
COMMENT ON TABLE mw_users IS 'Middleware users với subkey authentication (thay thế users.json)';
COMMENT ON TABLE mw_user_quotas IS 'Quota limits và usage tracking cho mỗi user';
COMMENT ON TABLE mw_request_logs IS 'Chi tiết mỗi API request (thay thế middleware.log)';
COMMENT ON TABLE mw_daily_usage IS 'Aggregated usage theo ngày cho dashboard';
COMMENT ON TABLE mw_model_prices IS 'Bảng giá models cho cost calculation (thay thế prices.json)';
COMMENT ON TABLE mw_pending_requests IS 'Pending streaming requests cho reconciliation';
