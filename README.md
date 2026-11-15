# Security-banking-app
A security-focused banking application that analyzes and detects potential cyber threats such as brute-force attacks and fraudulent activities, with security testing, data analysis, and automated report generation features. 🔐🏦

# GraphShield Security Banking App

GraphShield is a role-based banking security prototype built with a Flutter frontend and a Flask backend. It combines normal application authentication with a security scoring pipeline that uses feature engineering, ML scoring, graph relationships, and rule-driven decisions to detect suspicious login activity.

This project supports three main roles:

- `BANK`: A bank operator account that manages users for a specific bank and views security telemetry for that bank.
- `ADMIN`: A linked admin account that can also inspect bank-level security dashboards and subscription workflows.
- `USER`: A customer account linked to a bank.

The app also exposes a separate outsider-login security endpoint used to evaluate suspicious login attempts coming from outside systems. The dashboards are designed to focus on those suspicious outsider attempts, not normal in-app logins.

## What The Project Does

At a high level, the system has two parallel concerns:

1. Normal app access:
   Users, bank accounts, and admin accounts register and log in through the Flutter UI.

2. Security monitoring:
   External or suspicious login attempts can be submitted to the backend security endpoint. Those attempts are scored and, if suspicious, are stored as security events that appear in the dashboards.

The result is a demo app where:

- bank/admin users can approve pending end users
- users can log in after approval
- bank/admin dashboards show suspicious outsider login activity for the bank
- user dashboards show suspicious outsider attempts targeting that user
- subscription/trial logic controls bank access features

## Tech Stack

### Frontend

- Flutter
- Dart
- `http` for API calls
- `flutter_secure_storage` for token persistence
- `fl_chart` for analytics charts
- `graphview` for graph visualization

### Backend

- Flask
- Flask-CORS
- PyJWT
- bcrypt
- MongoDB for primary persistence
- Redis for rate limiting/session helpers
- Neo4j for graph relationships
- scikit-learn / LightGBM based model loading for risk scoring

## Main Roles And Their Flows

### 1. Bank

Bank registration creates a bank record plus a linked bank account. That account can:

- log in through `/api/v1/bank-login`
- view the admin-style dashboard scoped to its bank
- approve or reject pending users for its bank
- submit subscription requests after the free trial

### 2. Admin

Admin registration creates an account linked to an existing bank. That account can:

- log in through `/api/v1/login` with role `ADMIN`
- view the same bank-scoped dashboard data
- review subscription requests
- approve or reject user onboarding for the linked bank

### 3. User

User registration requires a selected bank. New users start in `PENDING` approval state. Once approved by a bank/admin account, the user can:

- log in through `/api/v1/login` with role `USER`
- view their personal dashboard
- see suspicious outsider login attempts associated with their account

## Important Current Behavior

The project currently separates:

- normal in-app authentication
- outsider suspicious login monitoring

Normal app logins for bank/admin/user accounts are used for access control, but they are not supposed to fill the dashboards. The dashboards are intended to display only suspicious outsider login attempts, especially `BLOCK`ed ones generated through the security pipeline.

## Project Structure

```text
security_banking_app/
|-- lib/
|   |-- main.dart
|   |-- screens/
|   |   |-- auth.dart
|   |   |-- admin_dashboard.dart
|   |   |-- user_dashboard.dart
|   |-- services/
|       |-- api_service.dart
|
|-- backend/
|   |-- app.py
|   |-- config.py
|   |-- requirements.txt
|   |-- auth/
|   |   |-- routes.py
|   |   |-- jwt_handler.py
|   |-- database/
|   |   |-- mongo.py
|   |   |-- redis_db.py
|   |   |-- graph_db.py
|   |-- engine/
|       |-- feature_engineering.py
|       |-- ml_engine.py
|       |-- decision_engine.py
|
|-- docker-compose.yml
|-- start_backend.bat
|-- README.md
```

## Frontend Overview

### `lib/main.dart`

This is the Flutter entry point. It:

- loads `.env`
- initializes `ApiService`
- restores the saved session if a token already exists
- routes the user to:
  - `AuthScreen` if logged out
  - `AdminDashboard` for `BANK` and `ADMIN`
  - `UserDashboard` for `USER`

### `lib/screens/auth.dart`

This screen handles:

- login tab
- register tab
- role selection
- bank selection for user/admin registration
- bank-name input for bank registration
- approval state messages for users

### `lib/screens/admin_dashboard.dart`

This dashboard is used by both `BANK` and `ADMIN`. It shows:

- subscription status
- subscription approvals
- system overview counts
- attempts-vs-days chart
- pending user approvals
- live threat feed
- graph insights
- user risk table
- alert panel

This dashboard is bank-scoped, so it only shows data for the linked bank.

### `lib/screens/user_dashboard.dart`

This is the customer-facing security dashboard. It shows:

- latest suspicious outsider attempt status
- activity notes
- suspicious outsider login history
- device history
- IP history

### `lib/services/api_service.dart`

This is the frontend API layer. It:

- stores and restores JWT access tokens
- decodes JWT payloads for role/user info
- sends all login, registration, dashboard, approval, and subscription requests
- clears session state on `401 Unauthorized`

## Backend Overview

### `backend/app.py`

This is the Flask application entry point. It:

- loads config
- initializes MongoDB
- initializes Redis
- initializes Neo4j
- initializes the ML and decision engines
- registers auth and security blueprints
- sets up CORS handling

### `backend/config.py`

This file reads environment variables such as:

- `SECRET_KEY`
- `MONGO_URI`
- `MONGO_DB_NAME`
- `REDIS_HOST`
- `REDIS_PORT`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `RISK_BLOCK_THRESHOLD`

### `backend/auth/routes.py`

This is the largest and most important backend file. It contains:

- bank listing
- registration
- user/admin login
- bank login
- logout
- subscription status and request workflow
- admin subscription approvals
- user dashboard
- admin dashboard
- graph insights
- graph data
- pending user approvals
- approve/reject user actions
- outsider security check endpoint
- active session helper
- blocked sites helper

### `backend/auth/jwt_handler.py`

This file handles:

- JWT generation
- token validation
- token blacklisting via Redis
- role-based route protection

### `backend/database/mongo.py`

This module initializes MongoDB and creates indexes used by the app. It also contains an in-memory fallback path so the app can still run in simplified environments if MongoDB is not available.

### `backend/database/redis_db.py`

This module initializes Redis for:

- lightweight rate limiting
- token/session helpers

If Redis is not available, it falls back to an in-memory mock implementation.

### `backend/database/graph_db.py`

This module wraps Neo4j operations for:

- logging user/device/IP/bank relationships
- generating graph topology data
- producing graph-based insights such as:
  - device reuse
  - botnet-style shared IP patterns
  - IP rotation
  - cross-bank device reuse

### `backend/engine/feature_engineering.py`

This file computes login-related features used by the ML pipeline, such as:

- failed attempts
- IP change count
- request interval
- session duration
- typing speed
- new-device flag
- VPN-like IP flag
- login hour

### `backend/engine/ml_engine.py`

This module loads the trained model artifacts and calculates an ML risk score using:

- a LightGBM classifier
- an anomaly model

### `backend/engine/decision_engine.py`

This module combines:

- engineered features
- ML score
- graph score

It then returns a final result including:

- `decision`
- `risk_score`
- `risk_level`
- `attack_type`
- explanation fields

## Core API Endpoints

### Auth And Registration

- `GET /api/v1/banks`
  Returns available banks for registration.

- `POST /api/v1/register`
  Registers a `BANK`, `ADMIN`, or `USER`.

- `POST /api/v1/login`
  Logs in `USER` and `ADMIN`.

- `POST /api/v1/bank-login`
  Logs in the bank account.

- `POST /api/v1/logout`
  Logs out the current session.

### Dashboard And Admin Actions

- `GET /api/v1/user/dashboard`
  Returns suspicious outsider events for the logged-in user.

- `GET /api/v1/admin/dashboard`
  Returns suspicious outsider events and analytics for the bank.

- `GET /api/v1/admin/graph-insights`
  Returns graph-based anomaly insights.

- `GET /api/v1/admin/graph-data`
  Returns graph visualization nodes and edges.

- `GET /api/v1/admin/pending-users`
  Lists users awaiting approval.

- `POST /api/v1/admin/approve-user`
  Approves a pending user.

- `POST /api/v1/admin/reject-user`
  Rejects a pending user.

### Subscription

- `GET /api/v1/subscription/status`
  Returns current trial/subscription status.

- `POST /api/v1/subscription/request`
  Submits a bank subscription request.

- `GET /api/v1/admin/subscription-requests`
  Lists pending subscription requests.

- `POST /api/v1/admin/subscription-requests/<request_id>/decision`
  Approves or rejects a subscription request.

### Security Monitoring

- `POST /api/security/check-login`
  Evaluates an outsider login attempt and stores suspicious results for dashboards.

- `GET /api/active-session`
  Returns active-session information for a token.

- `GET /api/blocked-sites`
  Returns blocked-site policy data.

## Data Flow

### Normal App Login

1. A bank/admin/user logs in from Flutter.
2. The backend validates credentials.
3. A JWT token is returned.
4. The frontend stores the token securely.
5. The user is routed to the correct dashboard.

These normal app logins are for access control and should not be the main security events shown in dashboards.

### Outsider Suspicious Login Flow

1. An external login attempt hits `/api/security/check-login`.
2. The backend resolves the bank and gathers historical context.
3. Features are computed.
4. The decision engine calculates ML score + graph score.
5. A final `ALLOW` or `BLOCK` decision is produced.
6. Suspicious outsider events are stored.
7. Bank/admin/user dashboards read those events.

## Local Development Setup

## Prerequisites

- Flutter SDK
- Python 3.10+ or 3.11
- MongoDB
- Redis
- Neo4j

Optional but helpful:

- Docker Desktop
- Google Chrome for web testing

### 1. Clone And Enter The Project

```powershell
cd d:\security_banking_app
```

### 2. Configure Frontend Environment

The root `.env` file currently contains:

```env
API_BASE_URL=http://127.0.0.1:5000
```

### 3. Install Flutter Packages

```powershell
flutter pub get
```

### 4. Install Backend Python Packages

```powershell
cd backend
pip install -r requirements.txt
```

### 5. Start The Databases

You can either:

- run MongoDB, Redis, and Neo4j directly on your machine
- or use Docker Compose

```powershell
docker compose up -d
```

### 6. Start The Backend

From the project root:

```powershell
start_backend.bat
```

Or manually:

```powershell
cd backend
python app.py
```

### 7. Start The Flutter App

From the project root:

```powershell
flutter run -d chrome
```

## Docker Notes

`docker-compose.yml` provides:

- MongoDB
- Redis
- Neo4j
- Flask backend

The backend Docker image is defined in [backend/Dockerfile](/abs/path/d:/security_banking_app/backend/Dockerfile).

## Typical Demo Flow

If you want to test the app from scratch:

1. Register a bank account.
2. Register an admin account and link it to that bank.
3. Register a user account under the same bank.
4. Log in as bank or admin.
5. Approve the pending user.
6. Log in as the user.
7. Trigger or insert outsider suspicious login attempts through the security endpoint.
8. Refresh dashboards and inspect the suspicious-event feed.

## Known Practical Notes

- User accounts require bank approval before login works.
- Bank and admin dashboards are bank-scoped.
- User dashboards are user-scoped.
- Subscription logic includes a free trial and admin approval flow.
- Redis and Mongo are important for full functionality.
- Neo4j improves graph insights, but some parts of the app still work without it.
- Some legacy/demo code still uses simplified assumptions because this is a prototype.

## Security Notes

This project is a prototype and should not be treated as a production banking platform without substantial hardening. Areas that would need improvement in a production environment include:

- secrets management
- stronger audit logging
- stricter password and account policies
- production-grade session management
- database backup/recovery strategy
- API abuse protection
- secure deployment configuration
- model governance and explainability controls

## In Short

GraphShield is a demo banking security platform where:

- Flutter provides the role-based UI
- Flask provides APIs and auth
- MongoDB stores operational and security data
- Redis supports rate/session helpers
- Neo4j powers graph insights
- ML and rules score outsider login attempts
- dashboards focus on suspicious outsider activity rather than normal app sign-ins
