/**
 * Agricultural Report System — Shared JavaScript
 *
 * Handles:
 * - SSE connection management
 * - Common UI interactions
 * - Clipboard utilities
 */

// ── SSE Client ──────────────────────────────────────────────────

class SSEClient {
    constructor(url, options = {}) {
        this.url = url;
        this.options = options;
        this.eventSource = null;
        this.listeners = {};
    }

    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
        return this;
    }

    emit(event, data) {
        const cbs = this.listeners[event] || [];
        cbs.forEach(cb => cb(data));
    }

    connect() {
        // Use fetch + ReadableStream for POST SSE
        // (EventSource only supports GET)
        return this._connectViaFetch();
    }

    async _connectViaFetch() {
        try {
            const resp = await fetch(this.url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.options.body || {}),
            });

            if (!resp.ok) {
                this.emit('error', { message: `HTTP ${resp.status}` });
                return;
            }

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                let currentEvent = 'message';

                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        currentEvent = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            this.emit(currentEvent, data);
                            if (currentEvent === 'error') {
                                this.emit('error', data);
                            }
                        } catch (e) {
                            // Not JSON, emit as text
                            this.emit(currentEvent, line.slice(6));
                        }
                        currentEvent = 'message';
                    }
                }
            }
        } catch (e) {
            this.emit('error', { message: e.message });
        }

        this.emit('close', {});
    }
}


// ── Formatting Utilities ─────────────────────────────────────────

function formatNumber(num) {
    if (num === null || num === undefined) return 'N/A';
    if (num >= 1e8) return (num / 1e8).toFixed(2) + '亿';
    if (num >= 1e4) return (num / 1e4).toFixed(2) + '万';
    return num.toLocaleString('zh-CN');
}


// ── Copy to Clipboard ────────────────────────────────────────────

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('已复制到剪贴板');
    }).catch(() => {
        showToast('复制失败，请手动复制');
    });
}


// ── Toast Notification ───────────────────────────────────────────

function showToast(message, duration = 3000) {
    // Remove existing toast
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg text-sm';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = 'opacity 0.3s';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}


// ── Expose to global scope ───────────────────────────────────────

window.SSEClient = SSEClient;
window.formatNumber = formatNumber;
window.copyToClipboard = copyToClipboard;
window.showToast = showToast;
