import json
try:
    import redis
except ImportError:
    redis = None
from django.conf import settings
from .base import BaseTrackingBackend


class RedisBatchTrackingBackend(BaseTrackingBackend):
    """Push tracking events to Redis list for batch flush."""
    def __init__(self):
        super().__init__()
        if not redis:
            raise Exception("Redis not installed")
        config = settings.MATOMO_API_TRACKING
        self.redis = redis.Redis.from_url(config["redis_url"])
        self.key = config.get("redis_key", "matomo_events")

    def send(self, params, meta):
        self.redis.rpush(
            self.key,
            json.dumps({"params": params, "meta": meta}),
        )