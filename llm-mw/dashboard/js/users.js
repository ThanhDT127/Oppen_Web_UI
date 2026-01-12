// Users tab logic - user management and RBAC
import { mwFetch } from './utils.js';
import { escapeHtml } from './utils.js';

// Load users data
export async function loadUsers() {
    try {
        const res = await mwFetch('/v1/_mw/admin/users');
        if (!res || !res.ok) return;
        
        const data = await res.json();
        if (!data || !data.users) return;

        const table = document.getElementById('usersTable');
        if (data.users.length > 0) {
            table.innerHTML = data.users.map(u => {
                // Map correct schema: active (not disabled), quota.used_cost_usd, quota.limit_cost_usd
                const status = u.active ? 'Active' : 'Disabled';
                const statusClass = u.active ? 'ok' : 'error';
                const costUsed = u.quota?.used_cost_usd ?? u.used_cost_usd ?? 0;
                const costLimit = u.quota?.limit_cost_usd ?? u.limit_cost_usd ?? 0;
                const limitDisplay = costLimit > 0 ? `$${costLimit.toFixed(4)}` : '∞';
                
                return `
                <tr>
                    <td>${escapeHtml(u.user_id)}</td>
                    <td>${escapeHtml(u.role || 'user')}</td>
                    <td class="status-${statusClass}">${status}</td>
                    <td>$${costUsed.toFixed(4)}</td>
                    <td>${limitDisplay}</td>
                    <td style="font-size: 11px; opacity: 0.7;">${escapeHtml((u.allowed_models || ['*']).join(', '))}</td>
                </tr>
                `;
            }).join('');
        } else {
            table.innerHTML = '<tr><td colspan="6">No users</td></tr>';
        }
    } catch (err) {
        console.error('Failed to load users:', err);
        document.getElementById('usersTable').innerHTML = '<tr><td colspan="6" class="error-msg">Error loading users</td></tr>';
    }
}
