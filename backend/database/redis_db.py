import logging
import time

import redis

logger = logging.getLogger(__name__)


class MockRedis:
    def __init__(self):
        self.store = {}
        self.expires = {}

    def set(self, key, value):
        self.store[key] = value

    def get(self, key):
        if key in self.expires and time.time() > self.expires[key]:
            self.delete(key)
            return None
        return self.store.get(key)

    def setex(self, key, time_secs, value):
        self.store[key] = value
        self.expires[key] = time.time() + time_secs

    def incr(self, key):
        val = self.get(key)
        if val is None:
            self.set(key, 1)
            return 1
        num = int(val) + 1
        self.set(key, num)
        return num

    def expire(self, key, time_secs):
        if key in self.store:
            self.expires[key] = time.time() + time_secs

    def delete(self, key):
        if key in self.store:
            del self.store[key]
        if key in self.expires:
            del self.expires[key]


redis_client = None


def init_redis(app):
    global redis_client

    host = app.config.get('REDIS_HOST', '127.0.0.1')
    port = app.config.get('REDIS_PORT', 6379)
    db = app.config.get('REDIS_DB', 0)

    try:
        real_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            socket_timeout=1,
        )
        real_client.ping()
        redis_client = real_client
        logger.info("Connected to Redis at %s:%s", host, port)
    except Exception:
        logger.warning("Failed to connect to Redis. Falling back to MockRedis in-memory store.")
        redis_client = MockRedis()


def get_redis():
    return redis_client
