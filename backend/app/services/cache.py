import redis
import json

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

def set_cache(key: str, value, ex: int = 3600):
    redis_client.set(key, json.dumps(value), ex=ex)

def get_cache(key: str):
    v = redis_client.get(key)
    if v is None:
        return None
    try:
        return json.loads(v)
    except Exception:
        return v

def invalidate_cache(key: str):
    redis_client.delete(key)