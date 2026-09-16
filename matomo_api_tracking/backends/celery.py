import logging
from ..tasks import send_matomo_tracking
from .base import BaseTrackingBackend
logger = logging.getLogger(__name__)


class CeleryTrackingBackend(BaseTrackingBackend):
    """Default backend: send via Celery."""

    def send(self, params, meta):
        try:
            send_matomo_tracking.delay(
                params, meta, matomo_url=self.url, timeout=self.timeout, token_auth=self.token_auth)
        except Exception as e:
            logger.error("cannot send tracking post: %s", e)
