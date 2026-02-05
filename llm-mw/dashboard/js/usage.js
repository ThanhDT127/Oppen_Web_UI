// Usage tab logic - metrics, charts, audit stream
import { mwFetch, updateStatus } from './utils.js';
import { currentTimeRange } from './filters.js';
import { addAuditEvent, clearAuditEvents } from './filters.js';
import { eventSource, setEventSource, setRetryCount, retryCount, MAX_RETRY_DELAY } from './auth.js';

// Load summary data
export async function loadSummary() {
    try {
        updateStatus('ok', 'Loading data...');
        
        // Build query params based on currentTimeRange
        const params = new URLSearchParams();
        if (currentTimeRange.minutes) {
            params.append('minutes', currentTimeRange.minutes);
        } else {
            params.append('start', currentTimeRange.start);
            params.append('end', currentTimeRange.end);
        }

        const res = await mwFetch(`/v1/_mw/summary?${params}`);
        if (!res) return; // 403 handled by mwFetch
        
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        
        const data = await res.json();
        
        // Debug: Log API response
        console.log('[Dashboard] Summary API response:', data);
        console.log('[Dashboard] Time range:', currentTimeRange);
        console.log('[Dashboard] API URL:', `/v1/_mw/summary?${params}`);
        
        if (!data || !data.totals) {
            console.warn('[Dashboard] No totals data in response');
            // Show helpful message if no data
            document.getElementById('topUsersTable').innerHTML = '<tr><td colspan="2" class="no-data">No data in selected time range.<br>Try "Last 7d" or "Last 30d"</td></tr>';
            document.getElementById('topModelsTable').innerHTML = '<tr><td colspan="2" class="no-data">No data in selected time range.<br>Try "Last 7d" or "Last 30d"</td></tr>';
            updateStatus('warning', 'No data in selected time range');
            return;
        }
        
        const t = data.totals;
        
        // Update metrics - read correct backend keys
        document.getElementById('metricLLMCalls').textContent = t.requests_total || 0;
        
        // NEW: Billable calls metric
        const billableElem = document.getElementById('metricBillableCalls');
        if (billableElem) {
            billableElem.textContent = t.billable_calls || 0;
        }
        
        // NEW: Usage missing warning
        const usageMissingElem = document.getElementById('metricUsageMissing');
        if (usageMissingElem) {
            const missingCount = t.usage_missing_calls || 0;
            usageMissingElem.textContent = missingCount;
            // Highlight if > 0 (indicates bug)
            if (missingCount > 0) {
                usageMissingElem.parentElement.classList.add('warning');
            } else {
                usageMissingElem.parentElement.classList.remove('warning');
            }
        }
        
        document.getElementById('metricPending').textContent = t.pending_open_count || 0;
        
        // Update breakdown
        document.getElementById('metricChat').textContent = t.chat_calls || 0;
        document.getElementById('metricImage').textContent = t.image_calls || 0;
        document.getElementById('metricAudio').textContent = t.audio_calls || 0;
        
        // Calculate error rate
        const errorRate = t.requests_total > 0 
            ? ((t.error_count || 0) / t.requests_total * 100) 
            : 0;
        document.getElementById('metricErrorRate').textContent = errorRate.toFixed(1) + '%';
        document.getElementById('metricLatency').textContent = 
            t.p95_latency_ms ? t.p95_latency_ms.toFixed(0) + 'ms' : '-';
        document.getElementById('metricTokens').textContent = 
            (t.tokens_total || 0).toLocaleString();
        document.getElementById('metricCost').textContent = 
            '$' + (t.cost_total_usd || 0).toFixed(4);
        
        // Update top users
        const usersTable = document.getElementById('topUsersTable');
        if (data.breakdown_by_user && data.breakdown_by_user.length > 0) {
            usersTable.innerHTML = data.breakdown_by_user.slice(0, 10).map(u => 
                `<tr><td>${u.user_id}</td><td>$${u.cost_usd.toFixed(6)}</td></tr>`
            ).join('');
        } else {
            usersTable.innerHTML = '<tr><td colspan="2">No data</td></tr>';
        }
        
        // Update top models
        const modelsTable = document.getElementById('topModelsTable');
        if (data.breakdown_by_model && data.breakdown_by_model.length > 0) {
            modelsTable.innerHTML = data.breakdown_by_model.slice(0, 10).map(m => 
                `<tr><td>${m.model}</td><td>$${m.cost_usd.toFixed(6)}</td></tr>`
            ).join('');
        } else {
            modelsTable.innerHTML = '<tr><td colspan="2">No data</td></tr>';
        }

        // Update charts with timeseries data
        const { updateCharts } = await import('./charts.js');
        updateCharts(data);
        
        updateStatus('ok', 'Authenticated ✓');
    } catch (err) {
        console.error('Failed to load summary:', err);
        updateStatus('error', `Load error: ${err.message}`);
        
        // Show error in tables
        document.getElementById('topUsersTable').innerHTML = '<tr><td colspan="2" class="error-msg">Error loading data</td></tr>';
        document.getElementById('topModelsTable').innerHTML = '<tr><td colspan="2" class="error-msg">Error loading data</td></tr>';
    }
}

// Connect to audit event stream
export function connectEventStream() {
    const eventsDiv = document.getElementById('events');
    
    // Close existing connection
    if (eventSource) {
        eventSource.close();
        setEventSource(null);
    }
    
    eventsDiv.innerHTML = '<div class="loading">Connecting to event stream...</div>';
    
    try {
        // EventSource automatically sends cookies (can't set headers)
        const es = new EventSource('/v1/_mw/stream');
        setEventSource(es);
        
        es.addEventListener('audit', (e) => {
            try {
                const data = JSON.parse(e.data);
                addAuditEvent(data);
                setRetryCount(0); // Reset on success
            } catch (err) {
                console.error('Failed to parse event:', err);
            }
        });
        
        es.onerror = async (e) => {
            console.error('EventSource error:', e);
            
            if (es.readyState === EventSource.CLOSED) {
                // Check if it's an auth issue by testing summary endpoint
                try {
                    const testRes = await fetch('/v1/_mw/summary?minutes=1', {
                        credentials: 'include'
                    });
                    
                    if (testRes.status === 403) {
                        // Auth failed - stop dashboard and show login
                        console.warn('Stream error: 403 auth failed');
                        eventsDiv.innerHTML = '<div class="error-msg">Authentication required. Please login.</div>';
                        
                        const { stopDashboard } = await import('./main.js');
                        stopDashboard();
                        
                        const { showLoginUI } = await import('./auth.js');
                        showLoginUI('Session expired. Please login again.');
                        return;
                    }
                } catch (testErr) {
                    console.error('Auth check failed:', testErr);
                }
                
                // Not an auth issue - do backoff reconnect
                const newRetryCount = retryCount + 1;
                setRetryCount(newRetryCount);
                const delays = [1000, 2000, 5000, 10000, MAX_RETRY_DELAY];
                const delay = delays[Math.min(newRetryCount - 1, delays.length - 1)];
                
                eventsDiv.innerHTML = `<div class="error-msg">Stream disconnected. Retrying in ${delay/1000}s... (attempt ${newRetryCount})</div>`;
                updateStatus('warning', `Stream disconnected, retry ${newRetryCount}`);
                
                // Reconnect with backoff
                setTimeout(() => {
                    if (document.getElementById('dashboard').classList.contains('hidden')) {
                        // User logged out, don't reconnect
                        return;
                    }
                    connectEventStream();
                }, delay);
            } else {
                // Connection error but still trying
                eventsDiv.innerHTML = '<div class="loading">Stream connection error, retrying...</div>';
            }
        };
        
        es.onopen = () => {
            clearAuditEvents();
            eventsDiv.innerHTML = '';
            setRetryCount(0);
            updateStatus('ok', 'Authenticated ✓ (Stream connected)');
        };
    } catch (err) {
        console.error('Failed to create EventSource:', err);
        eventsDiv.innerHTML = '<div class="error-msg">Failed to connect stream. Check console.</div>';
        updateStatus('error', 'Stream connection failed');
    }
}
