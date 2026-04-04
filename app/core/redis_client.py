import redis
from core.config import settings

REDIS_URL = settings.REDIS_URL

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=False
)



