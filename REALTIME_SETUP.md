# Eskwela Project - Real-Time Updates Setup Guide

## Overview

This guide explains how to enable and verify real-time updates in the Eskwela project using Django Channels and WebSockets.

## What is Real-Time Updates?

Real-time updates allow dashboard pages to automatically refresh when events occur (e.g., student status changes, new announcements) without requiring manual page reload.

## Architecture

- **Backend**: Django Channels with ASGI
- **Frontend**: WebSocket client (`realtime.js`)
- **Protocol**: WebSocket (`/ws/dashboard/`)
- **Channel Layer**: InMemoryChannelLayer (development) or Redis (production)

## Prerequisites

Ensure these packages are installed:

```bash
pip install django-channels
pip install daphne
```

To verify:

```bash
pip list | grep -E "channels|daphne"
```

## Running the Server

### ✅ CORRECT WAY (with WebSocket support)

Use Daphne ASGI server (includes WebSocket support):

```bash
# Option 1: Using the provided script
python run_server.py

# Option 2: Manual Daphne command
daphne -b 0.0.0.0 -p 8000 eskwela_project.asgi:application
```

### ❌ DON'T DO THIS (no WebSocket support)

```bash
# This WON'T work for WebSockets:
python manage.py runserver
```

Django's development server uses WSGI, which doesn't support WebSockets.

## Verifying Real-Time Connection

### 1. Check Server Logs

When you connect to a dashboard, you should see:

```
[DEBUG] 2026-03-01 10:15:30 landing.consumers connect() - WebSocket connected: student1 (42)
[INFO] 2026-03-01 10:15:30 landing.consumers connect() - User student1 added to dashboard_updates group
```

### 2. Browser DevTools

1. Open your browser's Developer Tools (F12)
2. Go to the **Network** tab
3. Filter by "WS" (WebSocket)
4. Look for a connection to `ws://localhost:8000/ws/dashboard/` or `wss://...`
5. Should show **101 Switching Protocols** (successful WebSocket handshake)

### 3. Real-Time Indicator

In the bottom-right corner of any dashboard page, you'll see a real-time status indicator:

- 🟢 **Green (Live)**: WebSocket connected and active
- 🟡 **Yellow (Connecting…)**: Attempting to establish connection
- 🔴 **Red (Offline)**: WebSocket disconnected, retrying

## Testing Real-Time Updates

### Test Announcements

1. Login as a **Teacher**
2. Create an announcement
3. Login as a **Student** (in another branch/incognito window)
4. Go to the **Announcements** page
5. The student should receive a toast notification about the new announcement

### Test Assignment Status

1. Login as a **Teacher** → Create an assignment
2. Login as a **Student** → Submit the assignment
3. Login as **Teacher** (refresh the page)
4. Grade the submission
5. Student browser should show a toast notification

### Test Student Approval

1. Login as **Admin** → Go to Admission Management
2. Have a pending student registration
3. In another window, stay on Admin Dashboard
4. Approve the student
5. The first Admin window should show a toast notification

## Common Issues & Solutions

### Issue 1: WebSocket Connection Failed

**Symptoms**: Red "Offline" indicator or console error: `WebSocket connection failed`

**Solutions**:

```bash
# 1. Verify Daphne is running (not runserver)
# Check console output for "Daphne starting" message

# 2. Check firewall/proxy not blocking WebSocket
# Try accessing the app on a different port:
daphne -b 0.0.0.0 -p 8001 eskwela_project.asgi:application

# 3. Verify ASGI application path is correct
# Your ASGI_APPLICATION setting should be:
ASGI_APPLICATION = "eskwela_project.asgi.application"
```

### Issue 2: Messages Not Broadcasting

**Symptoms**: Events happen but other users don't see notifications

**Check logs**:

```bash
# Look for errors in console like:
# [ERROR] Error broadcasting event 'student_status_changed'
```

**Solutions**:

```bash
# 1. Verify channel layer is configured (check settings.py):
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# 2. Check if broadcast_event is called correctly in views.py
# Should have: from .realtime_events import broadcast_event
#            broadcast_event('event_type', {'data': 'here'})

# 3. Restart the server after making changes
```

### Issue 3: "Channel Layer Not Configured" Warning

**Symptoms**: Console shows warning about channel layer not configured

**Solutions**:

```bash
# 1. Check CHANNEL_LAYERS in settings.py is defined
# 2. Verify import statement at top of settings:
from channels.layers import InMemoryChannelLayer

# 3. Ensure daphne is installed:
pip install daphne

# 4. Restart server
```

### Issue 4: Many UserID is 'None' Errors

**Symptoms**: WebSocket accepts unauthenticated users

**Why**: AuthMiddlewareStack should only accept authenticated users

**Solution**:

Ensure `landing/consumers.py` has this check:

```python
if not self.scope["user"].is_authenticated:
    await self.close()
    return
```

This is already in place. If you see unauthenticated connections, verify you're logged in before accessing dashboard pages.

## Production Deployment

For production, use a production-grade channel layer:

### Option 1: Redis Channel Layer

```bash
# Install Redis support
pip install channels_redis

# Update settings.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis_host", 6379)],
        },
    },
}
```

### Option 2: Production ASGI Servers

Instead of Daphne dev server, use:

- **Uvicorn** + **Gunicorn**
- **Hypercorn**
- **Production ASGI Middleware**

Example with Uvicorn + Gunicorn:

```bash
pip install uvicorn gunicorn
gunicorn -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 eskwela_project.asgi:application
```

## File Structure

Here's what each file does in the real-time system:

```
eskwela_project/
├── asgi.py                    # ASGI configuration (HTTP + WebSocket routing)
├── settings.py                # Django settings (includes CHANNEL_LAYERS config)
│
landing/
├── consumers.py              # WebSocket consumer (handles connections/messages)
├── routing.py                # WebSocket URL patterns
├── realtime_events.py        # broadcast_event() function
│
static/js/
└── realtime.js              # Client-side WebSocket + UI notifications

templates/
├── student/student_base.html        # Includes realtime.js, data-dashboard="student"
├── teacher/teacher_base.html        #    ''                 data-dashboard="teacher"
└── administrator/admin_base.html    #    ''                 data-dashboard="admin"
```

## Advanced: Custom Events

### Broadcast a Custom Event

In your views.py:

```python
from landing.realtime_events import broadcast_event

# When something happens:
broadcast_event('custom_event_name', {
    'id': 42,
    'message': 'Custom data here',
    'timestamp': str(timezone.now()),
})
```

### Listen to Events in JavaScript

In your page template:

```javascript
// Listen for custom events
RealtimeSync.on("custom_event_name", function (data) {
  console.log("Event received:", data);
  // Update your UI here
  // Example: update a counter, refresh a list, etc.
});

// Listen to ALL events
RealtimeSync.on("*", function (data) {
  console.log("Any event:", data.type);
});
```

## Debugging WebSocket Issues

### Enable Verbose Logging

In settings.py, change logging level:

```python
LOGGING = {
    # ... existing config ...
    "loggers": {
        "landing": {
            "level": "DEBUG",  # Change to DEBUG
        },
    },
}
```

Then check logs:

```bash
# View real-time logs
tail -f logs/debug.log | grep -i websocket

# Search for errors
grep -i "error" logs/debug.log
```

### Browser Console

Open DevTools console (F12) to see client-side errors:

```javascript
// If real-time indicator shows red:
console.error("WebSocket connection failed");

// If messages aren't received:
// Check Network tab → WS filter → look for failed connections
```

### Verify Django Channels Is Working

```bash
python manage.py shell

# Test channel layer
from channels.layers import get_channel_layer
import asyncio

async def test():
    channel_layer = get_channel_layer()
    print(channel_layer)  # Should print the channel layer backend

asyncio.run(test())
```

## Quick Start Checklist

- [ ] Installed: `pip install daphne channels`
- [ ] Running server with: `python run_server.py`
- [ ] WebSocket indicator shows 🟢 Green on dashboard
- [ ] Network tab shows WebSocket connection (101 status)
- [ ] Logs show: `WebSocket connected: [username]`
- [ ] Test event triggered → See toast notification
- [ ] Another browser receives the notification

## Support

If real-time updates still aren't working:

1. **Check server logs** for error messages
2. **Verify Daphne is running** (not Django runserver)
3. **Check browser console** (F12) for WebSocket errors
4. **Verify settings.py** has CHANNEL_LAYERS configured
5. **Restart the server** after making changes
6. **Clear browser cache** (Ctrl+Shift+Delete)
7. **Try a different port** in case firewall is blocking

---

**Last Updated**: March 2026
**Django Version**: 6.0+
**Channels Version**: 4.0+
