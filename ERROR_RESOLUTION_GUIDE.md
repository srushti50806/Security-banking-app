# Error Resolution Guide

## Summary of Errors

Your Flutter web app is experiencing connection issues with the backend. The errors are:

1. **404 NOT FOUND** on `/api/v1/bank-login`
2. **CORS Policy Violations** - Requests blocked by browser
3. **500 INTERNAL SERVER ERROR** on `/api/v1/login` and `/api/v1/admin/graph-data`
4. **401 UNAUTHORIZED** on login attempt

## Root Causes

### Issue 1: CORS Configuration
- **Symptom**: "Access to fetch...blocked by CORS policy"
- **Cause**: Backend wasn't explicitly configured to accept requests from frontend origin
- **Fix**: ✅ Updated `app.py` with explicit CORS configuration

### Issue 2: Database Not Initialized  
- **Symptom**: 500 errors on endpoints
- **Cause**: MongoDB, Redis, or Neo4j not running
- **Check**: Run `python backend/check_databases.py`

### Issue 3: Missing Authentication Token
- **Symptom**: 401 UNAUTHORIZED on `/api/v1/admin/graph-data`
- **Cause**: Protected endpoints require JWT token in Authorization header
- **Solution**: Frontend must send token after successful login

---

## How to Fix

### Step 1: Verify Databases Are Running

```bash
cd backend
python check_databases.py
```

**Expected Output:**
```
✓ MongoDB is running at 127.0.0.1:27017
✓ Redis is running at 127.0.0.1:6379
✓ Neo4j is running at bolt://localhost:7687
```

If any fail, start the services:

**MongoDB** (Windows):
```bash
# If installed via Chocolatey or downloaded binary
mongod
```

**Redis** (Windows):
```bash
# If installed via Chocolatey or WSL
redis-server
```

**Neo4j** (Windows):
```bash
# Start Neo4j desktop app or command line
neo4j console
```

### Step 2: Start Backend Server

```bash
cd backend
python app.py
```

You should see:
```
* Running on http://0.0.0.0:5000
 WARNING in werkzeug: This is a development server. Do not use it in production.
```

### Step 3: Verify CORS Fix

Test the health endpoint:
```bash
curl -X GET http://127.0.0.1:5000/api/v1/health \
  -H "Origin: http://localhost:50159" \
  -v
```

You should see response headers:
```
Access-Control-Allow-Origin: http://localhost:50159
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH
Access-Control-Allow-Headers: Content-Type, Authorization
```

### Step 4: Test Login Endpoint

```bash
curl -X POST http://127.0.0.1:5000/api/v1/login \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:50159" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

If databases are running and user exists, you'll get:
```json
{
  "token": "eyJ0...",
  "user_id": "...",
  "role": "USER",
  "bank_id": "...",
  ...
}
```

### Step 5: Restart Flutter App

After backend is running and CORS is fixed:

```bash
# In Flutter directory
flutter run -d chrome
```

The app should now be able to communicate with the backend.

---

## Changes Made to Backend

### `backend/app.py`
- Added explicit CORS configuration  
- Added `@app.after_request` handler to ensure CORS headers on all responses
- Added error handlers for 404 and 500 errors
- Imported `request` from Flask

### New File: `backend/check_databases.py`
- Diagnostic script to check database connectivity
- Run with: `python check_databases.py`

---

## Still Having Issues?

### Check Backend Logs
```bash
# Terminal where backend is running
# Look for ERROR or WARNING messages
```

### Check Browser Console
In Flutter DevTools or browser F12:
- Network tab: verify CORS headers are present
- Console tab: check actual error messages

### Verify Frontend Origin
The frontend might be running on a different port. Update allowed origins in `app.py` if needed:
```python
cors_config = {
    "origins": [
        "http://localhost:50159",  # Add your port here
        "http://127.0.0.1:50159",
    ],
    ...
}
```

### Database Connection Details
Update config in `backend/config.py` if using non-default ports:
```python
MONGO_URI = 'mongodb://127.0.0.1:27017/'
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
NEO4J_URI = 'bolt://localhost:7687'
```
