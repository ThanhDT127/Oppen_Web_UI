// Real-time Active Users SSE stream logic

let _eventSource = null;

export function connectActiveUsersStream() {
    if (_eventSource) {
        _eventSource.close();
    }

    const streamUrl = '/v1/_mw/admin/active-users/stream';
    _eventSource = new EventSource(streamUrl);

    _eventSource.addEventListener('active_users', (e) => {
        try {
            const data = JSON.parse(e.data);
            const count = data.active_users !== undefined ? data.active_users : 0;
            const el = document.getElementById('metricActiveUsers');
            if (el) {
                el.textContent = count;
            }
        } catch (err) {
            console.error('Failed to parse active users event:', err);
        }
    });

    _eventSource.addEventListener('error', (e) => {
        console.error('SSE Active Users connection error:', e);
        const el = document.getElementById('metricActiveUsers');
        if (el) {
            el.textContent = '?';
        }
        // EventSource will automatically retry connecting
    });
}

export function disconnectActiveUsersStream() {
    if (_eventSource) {
        _eventSource.close();
        _eventSource = null;
    }
}
