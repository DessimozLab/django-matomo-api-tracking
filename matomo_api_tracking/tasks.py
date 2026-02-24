import logging
import json
from celery import shared_task
from django.conf import settings

try:
    import redis
except ImportError:
    redis = None
from .transport import send_single_tracking_event, send_bulk_tracking_events

logger = logging.getLogger(__name__)


@shared_task
def send_matomo_tracking(params, meta, matomo_url, timeout):
    return send_single_tracking_event(params, meta, matomo_url, timeout)


@shared_task
def flush_matomo_batch(batch_size=500):
    """
    Flush Redis-stored Matomo events in batches.
    """
    if redis is None:
        raise Exception("Redis not installed")

    config = settings.MATOMO_API_TRACKING
    redis_url = config.get("redis_url")
    matomo_url = config.get('url')

    if not redis_url or not matomo_url:
        raise Exception("Matomo configuration incomplete")

    r = redis.Redis.from_url(redis_url)
    key = config.get("redis_key", "matomo_events")
    token_auth = config.get("TOKEN_AUTH")
    try:
        timeout = float(config.get("timeout", 8))
    except ValueError:
        timeout = 8

    events = []
    for _ in range(batch_size):
        item = r.lpop(key)
        if not item:
            break
        events.append(json.loads(item))

    if not events:
        return

    success = send_bulk_tracking_events(events, matomo_url, token_auth, timeout)
    if not success:
        logger.warning("Matomo tracking failed, events will be pushed back on queue.")
        for event in events:
            r.lpush(key, json.dumps(event))