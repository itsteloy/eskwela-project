/**
 * realtime.js
 *
 * Drop this file into your static folder and include it in BOTH
 * base.html (teacher) and your admin base template with:
 *
 *   <script src="{% static 'js/realtime.js' %}"></script>
 *
 * The script auto-detects the current dashboard type from the <body>
 * data attribute you add (see instructions below).
 *
 * HOW TO TAG YOUR TEMPLATES
 * --------------------------
 * Teacher base.html  → <body data-dashboard="teacher">
 * Admin base template → <body data-dashboard="admin">
 *
 * HOW TO BROADCAST AN EVENT (call from your existing JS)
 * ------------------------------------------------------
 *   RealtimeSync.broadcast('announcement_created', { id: 42, title: 'New post' });
 *   RealtimeSync.broadcast('student_status_changed', { id: 7, status: 'approved' });
 *
 * LISTENING FOR EVENTS
 * --------------------
 *   RealtimeSync.on('announcement_created', function(data) {
 *       // update your UI here
 *   });
 */

const RealtimeSync = (() => {
    const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/dashboard/`;
    const RECONNECT_DELAY_MS = 3000;
    const MAX_RECONNECT_ATTEMPTS = 10;

    let socket = null;
    let reconnectAttempts = 0;
    let listeners = {};   // { eventType: [callback, ...] }
    let pendingQueue = []; // messages queued while socket is connecting
    let dashboardType = document.body.dataset.dashboard || 'unknown';

    // ── Indicator badge ──────────────────────────────────────────────────── //
    function createIndicator() {
        const el = document.createElement('div');
        el.id = 'rt-indicator';
        el.style.cssText = `
            position: fixed; bottom: 18px; right: 18px; z-index: 9999;
            display: flex; align-items: center; gap: 7px;
            background: rgba(255,255,255,0.92); border-radius: 20px;
            padding: 6px 14px; box-shadow: 0 2px 12px rgba(0,0,0,0.12);
            font-size: 12px; font-family: inherit; color: #555;
            transition: opacity .4s;
        `;
        el.innerHTML = `<span id="rt-dot" style="width:9px;height:9px;border-radius:50%;background:#aaa;display:inline-block;"></span>
                        <span id="rt-label">Connecting…</span>`;
        document.body.appendChild(el);
        return el;
    }

    function setIndicator(state) {
        const dot = document.getElementById('rt-dot');
        const label = document.getElementById('rt-label');
        if (!dot) return;
        const map = {
            connecting: ['#f0ad4e', 'Connecting…'],
            live:       ['#28a745', 'Live'],
            error:      ['#dc3545', 'Offline — retrying…'],
        };
        const [color, text] = map[state] || ['#aaa', state];
        dot.style.background = color;
        label.textContent = text;
    }

    // ── Connection ───────────────────────────────────────────────────────── //
    function connect() {
        setIndicator('connecting');
        socket = new WebSocket(WS_URL);

        socket.onopen = () => {
            reconnectAttempts = 0;
            setIndicator('live');
            // Flush pending messages
            while (pendingQueue.length) {
                socket.send(pendingQueue.shift());
            }
        };

        socket.onmessage = (e) => {
            let msg;
            try { msg = JSON.parse(e.data); } catch { return; }
            handleIncoming(msg);
        };

        socket.onclose = () => {
            setIndicator('error');
            scheduleReconnect();
        };

        socket.onerror = () => {
            setIndicator('error');
        };
    }

    function scheduleReconnect() {
        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return;
        reconnectAttempts++;
        setTimeout(connect, RECONNECT_DELAY_MS * Math.min(reconnectAttempts, 5));
    }

    // ── Incoming message handler ──────────────────────────────────────────── //
    function handleIncoming(msg) {
        const type = msg.type;
        if (!type || type === 'connected' || type === 'pong') return;

        // Dispatch to registered listeners
        const cbs = listeners[type] || [];
        cbs.forEach(cb => { try { cb(msg); } catch (err) { console.error('[RealtimeSync]', err); } });

        // Generic "any" listeners
        (listeners['*'] || []).forEach(cb => { try { cb(msg); } catch (err) { console.error('[RealtimeSync]', err); } });

        // Built-in default handlers
        defaultHandler(msg);
    }

    // ── Default UI refresh handlers ────────────────────────────────────────── //
    function defaultHandler(msg) {
        switch (msg.type) {

            // ---------- ANNOUNCEMENTS ----------
            case 'announcement_created':
            case 'announcement_updated':
            case 'announcement_deleted':
                showToast('📢 Announcements updated — <a href="" onclick="location.reload();return false;">Refresh</a>');
                softRefreshSection('announcements-section', msg);
                break;

            // ---------- ASSIGNMENTS ----------
            case 'assignment_created':
            case 'assignment_updated':
            case 'assignment_deleted':
                showToast('📝 Assignments updated — <a href="" onclick="location.reload();return false;">Refresh</a>');
                softRefreshSection('assignments-section', msg);
                break;

            // ---------- SCHEDULES ----------
            case 'schedule_created':
            case 'schedule_updated':
            case 'schedule_deleted':
                showToast('🗓️ Schedule updated — <a href="" onclick="location.reload();return false;">Refresh</a>');
                softRefreshSection('schedules-section', msg);
                break;

            // ---------- MODULES ----------
            case 'module_created':
            case 'module_updated':
            case 'module_deleted':
                showToast('📚 Learning module updated — <a href="" onclick="location.reload();return false;">Refresh</a>');
                break;

            // ---------- STUDENT STATUS ----------
            case 'student_status_changed':
                handleStudentStatusChange(msg);
                break;

            // ---------- SUBMISSION GRADED ----------
            case 'submission_graded':
                if (dashboardType === 'student') {
                    showToast(`✅ Your submission for "<strong>${msg.assignment_title || 'an assignment'}</strong>" has been graded! <a href="" onclick="location.reload();return false;">View grade</a>`);
                }
                break;

            // ---------- NEW STUDENT REGISTERED ----------
            case 'student_registered':
                if (dashboardType === 'admin') {
                    showToast(`🆕 New student registration: <strong>${msg.name || 'A new student'}</strong> — <a href="" onclick="location.reload();return false;">Review now</a>`);
                }
                break;

            // ---------- ASSIGNMENT SUBMITTED ----------
            case 'assignment_submitted':
                if (dashboardType === 'teacher') {
                    showToast(`📥 <strong>${msg.student_name || 'A student'}</strong> submitted "<strong>${msg.assignment_title || 'an assignment'}</strong>" — <a href="" onclick="location.reload();return false;">View</a>`);
                }
                break;
        }
    }

    function handleStudentStatusChange(msg) {
        if (dashboardType === 'admin') {
            // Update the status badge in the students table without full reload
            const row = document.querySelector(`[data-student-id="${msg.id}"]`);
            if (row) {
                const badge = row.querySelector('.status-badge, .badge');
                if (badge) {
                    badge.textContent = msg.status;
                    badge.className = badge.className.replace(/badge-\w+/, '');
                    const colorMap = { approved: 'badge-success', pending: 'badge-warning', rejected: 'badge-danger' };
                    badge.classList.add(colorMap[msg.status] || 'badge-secondary');
                }
            }
            showToast(`🔔 Student status updated to <strong>${msg.status}</strong>`);
        } else if (dashboardType === 'teacher') {
            showToast('🔔 A student enrollment status has changed — <a href="" onclick="location.reload();return false;">Refresh</a>');
        }
    }

    /**
     * Soft-refresh a named section by re-fetching the current URL
     * and swapping only that section's innerHTML.
     */
    function softRefreshSection(sectionId, msg) {
        const section = document.getElementById(sectionId);
        if (!section) return; // section not on this page

        fetch(location.href, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(r => r.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const fresh = doc.getElementById(sectionId);
                if (fresh) {
                    section.innerHTML = fresh.innerHTML;
                    section.dispatchEvent(new CustomEvent('rt:refreshed', { detail: msg }));
                }
            })
            .catch(() => {}); // silently ignore — user can still manually refresh
    }

    // ── Toast notifications ───────────────────────────────────────────────── //
    function ensureToastContainer() {
        let c = document.getElementById('rt-toast-container');
        if (!c) {
            c = document.createElement('div');
            c.id = 'rt-toast-container';
            c.style.cssText = `
                position: fixed; top: 18px; right: 18px; z-index: 10000;
                display: flex; flex-direction: column; gap: 10px;
                max-width: 340px;
            `;
            document.body.appendChild(c);
        }
        return c;
    }

    function showToast(html, duration = 5000) {
        const container = ensureToastContainer();
        const toast = document.createElement('div');
        toast.style.cssText = `
            background: #fff; border-left: 4px solid #667eea;
            border-radius: 6px; padding: 12px 16px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.12);
            font-size: 13px; color: #333; line-height: 1.5;
            animation: rtSlideIn .3s ease;
        `;
        toast.innerHTML = html;
        container.appendChild(toast);

        // Inject animation keyframes once
        if (!document.getElementById('rt-style')) {
            const style = document.createElement('style');
            style.id = 'rt-style';
            style.textContent = `
                @keyframes rtSlideIn {
                    from { transform: translateX(120%); opacity: 0; }
                    to   { transform: translateX(0);    opacity: 1; }
                }
                @keyframes rtSlideOut {
                    from { transform: translateX(0);    opacity: 1; }
                    to   { transform: translateX(120%); opacity: 0; }
                }
                #rt-toast-container a { color: #667eea; }
            `;
            document.head.appendChild(style);
        }

        setTimeout(() => {
            toast.style.animation = 'rtSlideOut .3s ease forwards';
            setTimeout(() => toast.remove(), 320);
        }, duration);
    }

    // ── Public API ────────────────────────────────────────────────────────── //

    /** Register a listener for a specific event type (or '*' for all). */
    function on(eventType, callback) {
        if (!listeners[eventType]) listeners[eventType] = [];
        listeners[eventType].push(callback);
        console.log(`[RealtimeSync] Registered listener for: ${eventType}`);
    }

    /** Unregister a listener. */
    function off(eventType, callback) {
        if (!listeners[eventType]) return;
        listeners[eventType] = listeners[eventType].filter(cb => cb !== callback);
    }

    /** Broadcast an event to all connected dashboards. */
    function broadcast(eventType, data = {}) {
        const message = JSON.stringify({ type: eventType, ...data });
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(message);
            console.log(`[RealtimeSync] Event sent: ${eventType}`, data);
        } else {
            pendingQueue.push(message);
            console.warn(`[RealtimeSync] Event queued (socket not ready): ${eventType}`);
        }
    }

    /** Get connection status for debugging */
    function getStatus() {
        const map = {
            0: 'CONNECTING',
            1: 'OPEN',
            2: 'CLOSING',
            3: 'CLOSED',
        };
        return {
            isConnected: socket && socket.readyState === WebSocket.OPEN,
            readyState: map[socket?.readyState ?? 3],
            reconnectAttempts: reconnectAttempts,
            dashboardType: dashboardType,
            pendingMessages: pendingQueue.length,
        };
    }

    // ── Init ──────────────────────────────────────────────────────────────── //
    function init() {
        console.log('[RealtimeSync] Initializing real-time sync...');
        console.log('[RealtimeSync] Dashboard type:', dashboardType);
        createIndicator();
        connect();
    }

    document.addEventListener('DOMContentLoaded', init);

    return { on, off, broadcast, getStatus };
})();