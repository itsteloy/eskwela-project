# Quick Start Guide - Real-Time Updates

## 🚀 Getting Started (3 Steps)

### Step 1: Install Dependencies

```bash
pip install daphne channels
```

Verify installation:

```bash
pip list | grep -E "channels|daphne"
```

### Step 2: Start the Server (NOT with runserver)

```bash
# Use the provided script:
python run_server.py

# OR manually with Daphne:
daphne -b 0.0.0.0 -p 8000 eskwela_project.asgi:application
```

**Expected Output:**

```
Daphne starting up on 0.0.0.0:8000 (asgi:application)
Quit the server with CONTROL-C.
```

### Step 3: Verify It Works

1. Open browser → Dashboard (any page: student, teacher, or admin)
2. Check **bottom-right corner** for the real-time indicator
3. Should show 🟢 **Green "Live"** within a few seconds
4. Open **DevTools** (F12) → **Network** tab → Filter by "WS"
5. Should see a WebSocket connection

## ✅ Testing Real-Time Events

### Test 1: Create Announcement (Teacher → Student)

1. **Window A**: Login as Teacher → Create Announcement
2. **Window B**: Login as Student → Go to Announcements page
3. **Expected**: Toast notification pops up automatically

### Test 2: Grade Submission (Teacher → Student)

1. **Window A**: Login as Student → Submit Assignment
2. **Window B**: Login as Teacher → Grade the submission
3. **Window A**: Student should see notification about grading

### Test 3: Approve Student (Admin)

1. **Window A**: Login as Admin → Stay on Dashboard
2. **Window B**: Login as Admin → Approve a pending student
3. **Window A**: Should see automatic notification

## 🔴 Something Not Working?

### Check #1: Are you using Daphne?

```bash
# WRONG ❌
python manage.py runserver

# RIGHT ✅
python run_server.py
# OR
daphne -b 0.0.0.0 -p 8000 eskwela_project.asgi:application
```

### Check #2: WebSocket Connection

Open browser console (F12) and run:

```javascript
RealtimeSync.getStatus();
```

Output should look like:

```javascript
{
  isConnected: true,
  readyState: "OPEN",
  reconnectAttempts: 0,
  dashboardType: "student",
  pendingMessages: 0
}
```

**If `isConnected` is false:**

- Check Network tab for WebSocket errors
- Verify you're logged in
- Restart server

### Check #3: Server Logs

Look for these good signs in console:

```
[DEBUG] WebSocket connected: student1 (42)
[INFO] User student1 added to dashboard_updates group
[DEBUG] Broadcasting event: announcement_created
```

Bad signs (errors):

```
ERROR: Channel layer not configured
ERROR: WebSocket connection failed
```

## 📚 File Changes Made

### Backend Changes:

- ✅ `eskwela_project/asgi.py` - Enhanced ASGI configuration
- ✅ `landing/consumers.py` - Added logging and error handling
- ✅ `landing/realtime_events.py` - Added logging to broadcast_event()
- ✅ `eskwela_project/settings.py` - Added LOGGING configuration

### Frontend Changes:

- ✅ `static/js/realtime.js` - Added debugging methods and console logs
- ✅ All base templates have data-dashboard attribute and realtime.js included

### Helper Files:

- ✅ `run_server.py` - Easy startup script
- ✅ `REALTIME_SETUP.md` - Comprehensive setup guide
- ✅ `requirements.txt` - All dependencies

## 🎯 What Works Now

✅ Real-time dashboard updates
✅ WebSocket connections with authentication
✅ Toast notifications for events
✅ Automatic reconnection on disconnect
✅ Status indicator (green/yellow/red)
✅ Detailed logging for debugging
✅ Support for all event types:

- Student status changes
- Announcements
- Assignments
- Modules
- Schedules
- Submissions

## 📖 Full Documentation

Read the complete guide with troubleshooting:

```
REALTIME_SETUP.md
```

## 🆘 Still Having Issues?

1. **Read** `REALTIME_SETUP.md` - Common Issues & Solutions section
2. **Check** browser console (F12) for JavaScript errors
3. **Check** server logs for Python errors
4. **Verify** you're using Daphne, not runserver
5. **Restart** server after any code changes
6. **Clear** browser cache (Ctrl+Shift+Delete)

---

**TL;DR:**

```bash
pip install daphne channels
python run_server.py
# Open dashboard → Should see 🟢 Green indicator
# Test any event → Should see toast notification
```
