from rq import Queue
from core.redis_client import redis_client

execution_queue = Queue("execution_queue", connection=redis_client)
session_sync_queue = Queue("session_sync_queue", connection=redis_client)
logins_queue = Queue("logins_queue", connection=redis_client)


TASK_QUEUE_SIZE_LIMIT = 5
