# Live Code Execution, Analysis, and OAuth2 Auth System

This repository contains a Dockerized live-coding platform with:

- a React + Vite frontend packaged behind Nginx
- a FastAPI backend for sessions, execution, code analysis, and Google OAuth2 login
- PostgreSQL as the source of truth
- Redis + RQ for async execution and session-sync jobs
- a worker that runs learner code inside isolated Docker containers

## Table of Contents

- [1. Current System Summary](#1-current-system-summary)
- [2. Architecture Overview](#2-architecture-overview)
- [3. Main Modules](#3-main-modules)
- [4. End-to-End Runtime Flows](#4-end-to-end-runtime-flows)
  - [4.1 Session Creation](#41-session-creation)
  - [4.2 Autosave Flow](#42-autosave-flow)
  - [4.3 Execution Flow](#43-execution-flow)
  - [4.4 Analyzer Flow](#44-analyzer-flow)
  - [4.5 OAuth2 Login Flow](#45-oauth2-login-flow)
- [5. Frontend Behavior](#5-frontend-behavior)
- [6. API Surface](#6-api-surface)
  - [6.1 Session Endpoints](#61-session-endpoints)
  - [6.2 Execution Endpoints](#62-execution-endpoints)
  - [6.3 Analyzer Endpoints](#63-analyzer-endpoints)
  - [6.4 Auth Endpoints](#64-auth-endpoints)
  - [6.5 Example Analyzer Result](#65-example-analyzer-result)
  - [6.6 Example Analyzer WebSocket Message](#66-example-analyzer-websocket-message)
- [7. Supported Languages](#7-supported-languages)
  - [7.1 Execution](#71-execution)
  - [7.2 Analysis](#72-analysis)
- [8. Data Model](#8-data-model)
  - [8.1 `code_sessions`](#81-code_sessions)
  - [8.2 `executions`](#82-executions)
- [9. Redis Usage](#9-redis-usage)
- [10. Reliability and Safety Controls](#10-reliability-and-safety-controls)
  - [10.1 Reliability](#101-reliability)
  - [10.2 Execution Safety](#102-execution-safety)
- [11. Dockerized Services](#11-dockerized-services)
- [12. Setup](#12-setup)
  - [12.1 Prerequisites](#121-prerequisites)
  - [12.2 Pre-pull Runtime Images](#122-pre-pull-runtime-images)
  - [12.3 Start the Whole Stack](#123-start-the-whole-stack)
  - [12.4 Access the Services](#124-access-the-services)
  - [12.5 Stop the Stack](#125-stop-the-stack)
  - [12.6 Logs](#126-logs)
- [13. Local Development Notes](#13-local-development-notes)
  - [13.1 Backend](#131-backend)
  - [13.2 Frontend](#132-frontend)
- [14. Verification Status](#14-verification-status)
- [15. Known Gaps and Caveats](#15-known-gaps-and-caveats)
- [16. Recommended Next Improvements](#16-recommended-next-improvements)

## 1. Current System Summary

The current system supports four main capabilities:

1. Session editing with Redis-backed autosave and eventual DB sync
2. Asynchronous code execution for `python`, `java`, and `cpp`
3. Static code analysis for `python`, `java`, and `cpp`, exposed via both HTTP and WebSocket
4. Google OAuth2 login with JWT access token, JWT refresh token, and Redis-backed one-time code exchange

The frontend is now part of the Docker Compose stack and is served on `http://localhost:3000`. It proxies both REST and WebSocket traffic under `/api` to the FastAPI backend.

## 2. Architecture Overview

```text
Browser
  |
  v
UI Container (Nginx, port 3000)
  | \
  |  \ REST + WebSocket proxy (/api/*)
  v   v
FastAPI (port 8001)
  |        |             \
  |        |              \ enqueue
  |        |               v
  |        |         Redis + RQ
  |        |          - execution_queue
  |        |          - session_sync_queue
  |        |          - session snapshot cache
  |        |          - per-session execution lock
  |        v
  |    PostgreSQL
  |
  v
Analyzer Engine
  - Python AST rules
  - Java/C++ Tree-Sitter rules

RQ Worker
  |
  v
docker run --rm <runtime image>
  |
  v
Execution status + stdout/stderr persisted to PostgreSQL
```

## 3. Main Modules

- Backend entrypoint: `app/main.py`
- Session API: `app/api/code_session.py`
- Execution API: `app/api/execution.py`
- Analyzer API: `app/api/analyzer.py`
- Auth API: `app/api/auth.py`
- Session service: `app/services/code_session.py`
- Execution service: `app/services/execution.py`
- JWT service: `app/services/jwt_service.py`
- OAuth authorization service: `app/services/oauth_authorize_service.py`
- Auth Redis service: `app/services/redis_service.py`
- Execution worker logic: `app/utils/executor.py`
- Redis helpers: `app/utils/redis.py`
- Analyzer engine: `app/analysis/*`
- Frontend app shell: `UI/src/pages/ExecutionWorkspacePage.jsx`
- Frontend analyzer socket client: `UI/src/api/analyzerSocket.js`
- Compose stack: `docker-compose.yml`

## 4. End-to-End Runtime Flows

### 4.1 Session Creation

1. The client calls `POST /code-sessions`.
2. FastAPI creates a `code_sessions` row with `ACTIVE` status and a language template.
3. The same payload is written into Redis as the latest session snapshot.
4. The frontend stores `session_id` and begins working against that session.

### 4.2 Autosave Flow

1. The client updates code with `PATCH /code-sessions/{session_id}`.
2. The latest payload is written to Redis immediately.
3. A `session_sync_queue` job is enqueued once per short window.
4. The worker persists the Redis snapshot back into PostgreSQL.

This means Redis is the fast-write layer for editing, while PostgreSQL remains the long-term source of truth.

### 4.3 Execution Flow

1. The client calls `POST /code-sessions/{session_id}/run`.
2. The backend cancels any previous `QUEUED` or `RUNNING` execution for that session.
3. A new execution row is inserted with `QUEUED`.
4. The job is pushed into `execution_queue`.
5. The worker loads the session, applies the latest Redis snapshot if present, and acquires a per-session Redis lock.
6. The worker checks that the required runtime image already exists locally.
7. The worker runs the code with `docker run`.
8. PostgreSQL is updated with status, timestamps, output, and execution time.
9. The frontend polls `GET /executions/{execution_id}` until a terminal state is reached.

### 4.4 Analyzer Flow

The analyzer is exposed in two ways:

- `POST /analyzer` for request/response analysis
- `WS /analyzer/ws/{session_id}` for live analysis

The current frontend uses the WebSocket path:

1. The UI opens an analyzer socket.
2. Source changes are debounced on the client.
3. The UI sends `analyze.request` messages with a monotonically increasing `version`.
4. The backend runs the analyzer and returns `analyze.result`.
5. The UI ignores stale versions and only renders the latest result.

### 4.5 OAuth2 Login Flow

The Google login flow uses authorization code + a backend-issued one-time exchange code:

1. The client calls `GET /auth/oauth2/google/authorize`.
2. FastAPI validates the frontend redirect against an allowlist and generates a short-lived JWT `state`.
3. The browser is redirected to Google OAuth.
4. Google redirects back to `GET /auth/oauth2/google/callback?code=...&state=...`.
5. FastAPI validates the `state`, exchanges the Google code, fetches Google user info, and simulates user provisioning.
6. FastAPI creates:
   - a short-lived JWT access token
   - a long-lived JWT refresh token with `jti`
7. The token pair is stored in Redis behind a random one-time code with a 60-second TTL.
8. FastAPI redirects the browser to the frontend success URL with `?code=<one-time-code>`.
9. The frontend calls `POST /auth/oauth2/exchange`.
10. FastAPI atomically consumes the code with Redis `GETDEL`, returns the access token in JSON, and sets the refresh token as an `HttpOnly` cookie.

## 5. Frontend Behavior

The React UI provides:

- language selector with built-in templates
- session creation and save controls
- async run button with execution polling
- runtime output tab for `stdout`, `stderr`, and execution time
- analysis tab with:
  - score card
  - issue badge count
  - severity-colored alert cards
  - confidence bars
  - expandable detail and fix text

The analyzer tab is backed by WebSocket, not HTTP polling.

For authentication, the intended frontend flow is:

- redirect the browser to `/auth/oauth2/google/authorize`
- read the `code` query parameter on the login success page
- call `POST /auth/oauth2/exchange`
- store only the access token in frontend memory
- rely on the `HttpOnly` refresh-token cookie for rotation via `POST /auth/refresh`

## 6. API Surface

Base URLs:

- Packaged UI: `http://localhost:3000`
- Backend direct: `http://localhost:8001`
- Swagger UI: `http://localhost:8001/docs`

### 6.1 Session Endpoints

- `POST /code-sessions`
  - Create a new session with template code for the selected language.
- `PATCH /code-sessions/{session_id}`
  - Update `language` and `source_code`.
- `GET /code-sessions/{session_id}`
  - Return the latest session state plus the latest execution.
- `GET /code-sessions/{session_id}/executions`
  - Return paginated execution history for the session.
- `POST /code-sessions/{session_id}/run`
  - Enqueue a new async execution job.

### 6.2 Execution Endpoints

- `GET /executions/{execution_id}`
  - Return the execution state and output.
- `POST /executions/{execution_id}/cancel`
  - Attempt to cancel a `QUEUED` or `RUNNING` execution.
- `POST /executions/{execution_id}/retry`
  - Present in the route table but currently not implemented.

### 6.3 Analyzer Endpoints

- `GET /analyzer/languages`
  - Return supported analyzer languages.
- `POST /analyzer`
  - Run analyzer over a single request.
- `WS /analyzer/ws/{session_id}`
  - Live analysis channel with `ping`, `pong`, `analyze.request`, `analyze.result`, and `analyze.error`.

### 6.4 Auth Endpoints

- `GET /auth/oauth2/google/authorize`
  - Redirect to Google OAuth with JWT `state`, `openid email profile`, `access_type=offline`, and `prompt=consent`.
- `GET /auth/oauth2/google/callback`
  - Validate `state`, exchange the Google code, fetch the Google profile, create access/refresh JWTs, store them behind a one-time Redis code, and redirect to the frontend with that code only.
- `POST /auth/oauth2/exchange`
  - Consume the one-time Redis code atomically and return the access token while setting the refresh token as an `HttpOnly` cookie.
- `POST /auth/refresh`
  - Verify the refresh cookie, check the refresh-token `jti` in Redis, rotate the refresh token, and return a new access token.

### 6.5 Example Analyzer Result

```json
{
  "language": "python",
  "result": {
    "alerts": [
      {
        "kind": "infinite_loop",
        "severity": "critical",
        "line": 1,
        "message": "Unconditional infinite loop with no exit path",
        "detail": "`while True` has no break, return, or exit call.",
        "fix": "Add a break condition or update a guard variable inside the loop.",
        "confidence": 0.97
      }
    ],
    "score": 70.0,
    "summary": "1 critical issue(s) detected.",
    "parse_error": null
  }
}
```

### 6.6 Example Analyzer WebSocket Message

Request:

```json
{
  "type": "analyze.request",
  "version": 7,
  "request_id": "7",
  "language": "python",
  "source_code": "while True:\n    pass"
}
```

Response:

```json
{
  "type": "analyze.result",
  "session_id": "workspace-live-analysis",
  "version": 7,
  "language": "python",
  "request_id": "7",
  "took_ms": 0.349,
  "result": {
    "alerts": [
      {
        "kind": "infinite_loop",
        "severity": "critical",
        "line": 1,
        "message": "Unconditional infinite loop with no exit path",
        "detail": "`while True` has no break, return, or exit call.",
        "fix": "Add a break condition or update a guard variable inside the loop.",
        "confidence": 0.97
      }
    ],
    "score": 70.0,
    "summary": "1 critical issue(s) detected.",
    "parse_error": null
  }
}
```

## 7. Supported Languages

### 7.1 Execution

Execution is implemented for:

- `python`
- `java`
- `cpp`

Configured runtime images:

- `python:3.11`
- `eclipse-temurin:17`
- `gcc:13`

### 7.2 Analysis

Static analysis currently supports:

- `python`
- `java`
- `cpp`

Implementation strategy:

- Python uses Python AST rules
- Java and C++ use Tree-Sitter parsing and rule sets

## 8. Data Model

### 8.1 `code_sessions`

- `id` UUID primary key
- `status` (`ACTIVE`, `INACTIVE`)
- `language`
- `source_code`
- `created_at`
- `updated_at`

### 8.2 `executions`

- `id` UUID primary key
- `session_id` foreign key to `code_sessions.id`
- `status` (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `TIMEOUT`, `CANCELLED`)
- `stdout`
- `stderr`
- `execution_time_ms`
- `created_at`
- `queued_at`
- `running_at`
- `completed_at`
- `failed_at`
- `timeout_at`
- `cancelled_at`

## 9. Redis Usage

Redis is used for more than just queueing:

1. RQ queues
   - `execution_queue`
   - `session_sync_queue`
2. Latest session snapshot cache
   - `session:{session_id}:latest`
3. Session sync enqueue flag
   - `session:{session_id}:sync-enqueued`
4. Per-session execution lock
   - `lock:session:{session_id}`
5. OAuth one-time code exchange
   - `auth:code:{uuid}`
6. Refresh-token session tracking
   - `auth:refresh:{jti}`

## 10. Reliability and Safety Controls

### 10.1 Reliability

- Async execution through Redis + RQ
- Queue backlog protection with `TASK_QUEUE_SIZE_LIMIT = 5`
- Retry on execution enqueue: `Retry(max=3, interval=[10, 30, 60])`
- Retry on session sync enqueue: `Retry(max=3, interval=[1, 5, 10])`
- Per-session Redis lock to prevent concurrent overlapping runs
- Timestamped execution lifecycle transitions
- Redis snapshot applied before execution so worker uses the latest code
- Runtime image preflight check to fail fast when images are missing locally
- OAuth refresh token rotation backed by Redis `jti` tracking

### 10.2 Execution Safety

The Python execution path uses:

- `--memory=256m`
- `--cpus=0.5`
- `--read-only`
- `--pids-limit=50`
- `--cap-drop=ALL`
- `--network none`
- `--rm`

The compiled-language path (`java`, `cpp`) also uses container isolation and a shared Docker volume workspace, but it skips `--read-only` because source files and build artifacts must be written inside the mounted workspace.

Auth-specific controls now in place:

- OAuth `state` is a short-lived JWT to protect against CSRF on callback.
- Frontend redirects are validated against an explicit allowlist to block open redirects.
- Access and refresh tokens are never returned in the browser redirect URL.
- One-time exchange codes are random UUIDs with 60-second TTL and single-use Redis `GETDEL`.
- Refresh tokens are delivered only through an `HttpOnly` cookie.

## 11. Dockerized Services

`docker-compose.yml` currently defines:

- `postgres`
  - PostgreSQL 15
  - exposed on `localhost:5432`
- `pgadmin`
  - exposed on `http://localhost:5050`
- `redis`
  - Redis 7
  - exposed on `localhost:6379`
- `fastapi-app`
  - FastAPI backend on `http://localhost:8001`
- `worker`
  - RQ worker for execution and session sync
- `ui`
  - packaged React frontend served by Nginx on `http://localhost:3000`

The UI container proxies:

- REST calls under `/api/*`
- analyzer WebSocket upgrades under `/api/analyzer/ws/*`

## 12. Setup

### 12.1 Prerequisites

- Docker Desktop
- Docker Compose v2

### 12.2 Pre-pull Runtime Images

Pull runtime images before the first execution:

```bash
docker pull python:3.11
docker pull eclipse-temurin:17
docker pull gcc:13
```

Without these images, the worker will fail fast with a clear `FAILED` status telling you which image is missing.

### 12.3 Start the Whole Stack

```bash
docker compose up --build
```

### 12.4 Access the Services

- UI: `http://localhost:3000`
- Backend: `http://localhost:8001`
- Swagger UI: `http://localhost:8001/docs`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- pgAdmin: `http://localhost:5050`

### 12.5 Stop the Stack

```bash
docker compose down
```

Remove volumes as well:

```bash
docker compose down -v
```

### 12.6 Logs

```bash
docker compose logs -f <service-name>
```

Examples:

- `docker compose logs -f fastapi-app`
- `docker compose logs -f worker`
- `docker compose logs -f ui`

## 13. Local Development Notes

### 13.1 Backend

Backend environment variables are loaded from `app/.env`:

- `DATABASE_URL=postgresql+psycopg2://admin:123456@postgres:5432/code_execution`
- `REDIS_URL=redis://redis:6379/0`
- `GOOGLE_CLIENT_ID=...`
- `GOOGLE_CLIENT_SECRET=...`
- `GOOGLE_REDIRECT_URI=http://localhost:8001/auth/oauth2/google/callback`
- `AUTH_FRONTEND_SUCCESS_REDIRECT_URI=http://localhost:3000/login/success`
- `AUTH_REDIRECT_ALLOWLIST=http://localhost:3000/login/success,http://localhost:5173/login/success`
- `BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173`
- `AUTH_COOKIE_SECURE=false` for local HTTP development only

### 13.2 Frontend

The frontend uses `VITE_API_BASE_URL` if provided; otherwise it defaults to `/api`.

In development, `UI/vite.config.js` proxies `/api` to `http://localhost:8001` and also allows WebSocket proxying for the analyzer channel.

If the frontend runs on a separate origin such as `http://localhost:5173`, requests that need refresh-cookie support must include credentials.

## 14. Verification Status

Verification commands for the current repository:

- Backend tests:

```bash
python -m pytest -q -p no:cacheprovider test
```

- Frontend production build:

```bash
cd UI
npm run build
```

- Dockerized UI build:

```bash
docker compose build ui
```

- Packaged UI availability:

```bash
docker compose up -d ui
curl -I http://localhost:3000
```

- Analyzer WebSocket through packaged UI:

```text
ws://localhost:3000/api/analyzer/ws/workspace-live-analysis
```

- OAuth2 backend tests are included in:
  - `test/test_auth_services.py`
  - `test/test_auth_api.py`
- OAuth2 manual verification requires valid Google OAuth credentials and a redirect URL included in both Google Console and `AUTH_REDIRECT_ALLOWLIST`.

## 15. Known Gaps and Caveats

- `POST /executions/{execution_id}/retry` is still a stub and returns `None`.
- Schema creation uses `Base.metadata.create_all()` and does not provide full migration management. Alembic is not integrated yet.
- The Java/C++ execution path mounts a hardcoded Docker volume name: `live-code-execution-system_shared_workspace`. If the Compose project name changes, compiled execution may need adjustment.
- The worker requires access to the host Docker daemon via `/var/run/docker.sock`.
- Google OAuth2 login now exists, but the session/execution APIs are not yet protected by access-token dependencies.
- There is still no rate limiting.
- Observability is still basic; there is no metrics or tracing pipeline.

## 16. Recommended Next Improvements

- Add Alembic migrations
- Implement retry semantics for executions
- Replace the hardcoded workspace volume name with a derived or configured value
- Add integration tests against real PostgreSQL, Redis, and worker containers
- Enforce access-token authentication on session and execution routes
- Bind sessions and executions to a real persisted user model
- Add per-user resource limits and rate limiting
- Add structured metrics for queue depth, execution latency, and analyzer latency
