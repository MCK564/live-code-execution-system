# Live Code Execution System

Backend take-home assignment implementation for a live coding feature inside a Job Simulation platform.

## 1. Objective

This service allows learners to:

- Create a live coding session.
- Continuously autosave code.
- Execute code asynchronously.
- Poll execution results with runtime status and output.

It is designed around queue-based background execution, basic sandboxing, and clear execution lifecycle tracking.

## 2. Tech Stack

- Backend framework: FastAPI
- Database: PostgreSQL + SQLAlchemy ORM
- Queue: Redis + RQ
- Worker: Python RQ worker
- Containerization: Docker + Docker Compose
- Tests: pytest (service-layer unit tests)

## 3. Architecture Overview

```text
Client
  |
  v
FastAPI (API Layer)
  |                    \
  |                     \ enqueue
  v                      v
PostgreSQL          Redis Queue (execution_queue)
                          |
                          v
                     RQ Worker
                          |
                          v
                 Isolated code run (docker run --rm)
                          |
                          v
                     Update execution row
```

Main modules:

- API layer: `app/api/*`
- Services: `app/services/*`
- Queue config: `app/core/task_queue.py`
- Worker process: `app/core/worker.py`
- Execution engine: `app/utils/executor.py`
- Data models: `app/models/*`

## 4. End-to-End Flow

### 4.1 Session creation

1. Client calls `POST /code-sessions`.
2. API creates a `code_sessions` row with `ACTIVE` status.
3. Returns `session_id`.

### 4.2 Autosave

1. Client calls `PATCH /code-sessions/{session_id}` frequently.
2. API updates `language` and `source_code` in DB.
3. Returns session metadata.

### 4.3 Run execution (async)

1. Client calls `POST /code-sessions/{session_id}/run`.
2. API creates `executions` row with `QUEUED` status.
3. Job is enqueued to Redis.
4. API returns immediately (`execution_id`, `QUEUED`).

### 4.4 Background execution + polling

1. Worker picks job.
2. Worker sets `RUNNING` and runs code in isolated Docker process.
3. Worker writes `stdout`, `stderr`, `execution_time_ms`, final status.
4. Client polls `GET /executions/{execution_id}` until terminal state.

## 5. API Documentation

Base URL (local Docker): `http://localhost:8001`

### 5.1 Create session

- Method: `POST`
- Path: `/code-sessions`
- Request:

```json
{
  "language": "python"
}
```

- Response:

```json
{
  "session_id": "uuid",
  "status": "ACTIVE"
}
```

### 5.2 Autosave code

- Method: `PATCH`
- Path: `/code-sessions/{session_id}`
- Request:

```json
{
  "language": "python",
  "source_code": "print('Hello World')"
}
```

- Response:

```json
{
  "session_id": "uuid",
  "status": "ACTIVE"
}
```

### 5.3 Run code asynchronously

- Method: `POST`
- Path: `/code-sessions/{session_id}/run`
- Response:

```json
{
  "execution_id": "uuid",
  "status": "QUEUED"
}
```

### 5.4 Get execution result

- Method: `GET`
- Path: `/executions/{execution_id}`
- Response:

```json
{
  "execution_id": "uuid",
  "status": "COMPLETED",
  "stdout": "Hello World\n",
  "stderr": "",
  "execution_time_ms": 120,
  "queued_at": "2026-03-18T13:05:00.000000+00:00",
  "running_at": "2026-03-18T13:05:01.000000+00:00",
  "completed_at": "2026-03-18T13:05:01.120000+00:00",
  "failed_at": null,
  "timeout_at": null
}
```

Execution states:

- `QUEUED`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `TIMEOUT`

## 6. Data Model

### 6.1 `code_sessions`

- `id` (UUID, PK)
- `status` (`ACTIVE` or `INACTIVE`)
- `language`
- `source_code`
- `created_at`
- `updated_at`

### 6.2 `executions`

- `id` (UUID, PK)
- `session_id` (FK -> `code_sessions.id`)
- `status` (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `TIMEOUT`)
- `stdout`
- `stderr`
- `execution_time_ms` (Integer)
- `created_at`
- `queued_at`
- `running_at`
- `completed_at`
- `failed_at`
- `timeout_at`

## 7. Reliability, Lifecycle, and Failure Handling

Lifecycle transition:

- `QUEUED -> RUNNING -> COMPLETED | FAILED | TIMEOUT`

Current reliability controls:

- Queue-based async execution (API is not blocked by runtime work).
- Retry policy on enqueue (`Retry(max=3, interval=[10,30,60])`).
- Per-session Redis lock to prevent concurrent execution overlap on the same session.
- Queue backlog guard via `TASK_QUEUE_SIZE_LIMIT = 5`.
- Custom not-found exception handler for missing session/execution.
- Stage timestamps (`queued_at`, `running_at`, `completed_at`, `failed_at`, `timeout_at`).

Failure modes handled:

- Session not found.
- Unsupported language.
- Runtime timeout.
- Runtime process error.
- Queue overload (`System is busy, please try again later`).

## 8. Safety Controls

Current code execution restrictions:

- Language restriction (`python` only for execution path).
- Time limit (`EXECUTION_TIME_LIMIT = 10` seconds).
- Docker runtime constraints:
  - `--memory=256m`
  - `--cpus=0.5`
  - `--read-only`
  - `--pids-limit=50`
  - `--cap-drop=ALL`
  - `--network none`
  - `--rm`

## 9. Scalability Considerations

Current approach:

- Async queue decouples API and execution workload.
- Worker can be scaled horizontally (`docker compose up --scale worker=N`).
- Queue size limit protects system from unlimited backlog growth.

Potential bottlenecks:

- Cold start overhead from `docker run` per execution.
- Single Redis instance.
- DB write contention under heavy load.

Mitigation ideas:

- Warm container pool + `docker exec` strategy.
- API rate limiting at gateway layer.
- Split queues by priority/language.
- Add dead-letter handling and replay controls.

## 10. Setup Instructions

### 10.1 Prerequisites

- Docker Desktop
- Docker Compose v2

### 10.2 Run all services

```bash
docker compose up --build
```

Services:

- FastAPI: `http://localhost:8001`
- Swagger UI: `http://localhost:8001/docs`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- pgAdmin: `http://localhost:5050`

### 10.3 Stop services

```bash
docker compose down
```

To remove persisted DB/Redis volumes:

```bash
docker compose down -v
```
 
### 10.4 Check logs
```bash
docker compose logs -f <image_name>
```

## 11. Environment Variables

Defined in `app/.env`:

- `DATABASE_URL=postgresql+psycopg2://admin:123456@postgres:5432/code_execution`
- `REDIS_URL=redis://redis:6379/0`

## 12. Schema Migration Note

`Base.metadata.create_all()` does not alter existing tables.

If you already have old `executions` schema, add new columns manually:

```sql
ALTER TABLE executions ADD COLUMN IF NOT EXISTS queued_at TIMESTAMPTZ;
ALTER TABLE executions ADD COLUMN IF NOT EXISTS running_at TIMESTAMPTZ;
ALTER TABLE executions ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE executions ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ;
ALTER TABLE executions ADD COLUMN IF NOT EXISTS timeout_at TIMESTAMPTZ;
ALTER TABLE executions ALTER COLUMN execution_time_ms TYPE INTEGER USING
(
  CASE
    WHEN execution_time_ms IS NULL THEN NULL
    WHEN execution_time_ms::text ~ '^[0-9]+$' THEN execution_time_ms::text::INTEGER
    ELSE NULL
  END
);
UPDATE executions SET queued_at = created_at WHERE queued_at IS NULL;
```

## 13. Tests

Implemented service-layer unit tests:

- `test/test-sessions.py`
- `test/test-execution.py`

These tests mock DB/queue behavior and do not require starting full platform.

PowerShell example:

```powershell
$env:DATABASE_URL='sqlite:///./unit-test.db'
$env:REDIS_URL='redis://localhost:6379/0'
python -m pytest -q -p no:cacheprovider test/test-sessions.py test/test-execution.py 2>&1 | Tee-Object -FilePath test-results.txt
```

Latest run summary:

- `7 passed in 1.32s` (see `test-results.txt`)

## 14. Design Decisions and Trade-offs

Decisions:

- FastAPI + SQLAlchemy for fast implementation and readable API layer.
- Redis/RQ for simple async worker model.
- PostgreSQL as source of truth for execution state.
- Docker-per-execution for stronger isolation than direct subprocess.

Trade-offs:

- Chosen simplicity and delivery speed over full production hardening.
- `docker run` per request improves isolation but adds startup latency.
- Basic queue-limit protection exists, but advanced abuse control can be improved.

## 15. What I Would Improve With More Time

- Add Alembic migrations and migration automation.
- Add API-level rate limiting and per-user quotas.
- Add dead-letter queue and richer retry telemetry.
- Add idempotency key for execution requests.
- Add stronger observability (structured logs, metrics, traces).
- Add integration tests against real PostgreSQL/Redis in CI.
- Expand language support with compile pipelines (Java/C++).

## 16. Assignment Checklist Mapping

- API layer (routes/controllers): done.
- Queue producer/consumer: done.
- Execution worker logic: done.
- Data models: done.
- Dockerfile + docker-compose: done.
- Setup + architecture + API docs + trade-offs: documented in this README.
- Unit tests: implemented for services.
- Integration tests and failure-infra tests: not fully implemented yet.
