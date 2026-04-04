from __future__ import annotations

from rq import Worker

from core.redis_client import redis_client


worker = Worker(["execution_queue", "session_sync_queue"], connection=redis_client)
worker.work()
