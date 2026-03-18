from core.redis_client import redis_client
from rq import Worker
import logging
import json, time
from core.task_queue import execution_queue

worker = Worker(["execution_queue"], connection=redis_client)
worker.work()



while True:
    result = redis_client.brpop("execution_queue", timeout=0)
    if result:
        logging.info("Processing task: %s", result[1])
        _,raw = result
        job = json.loads(raw)
        logging.info("Job: %s", job)

