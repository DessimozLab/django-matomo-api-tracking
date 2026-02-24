from ..tasks import send_matomo_tracking
from .base import BaseTrackingBackend


class DirectTrackingBackend(BaseTrackingBackend):
    """Send immediately (no Celery), useful for testing."""
    def send(self, params, meta, timeout):
        send_matomo_tracking(params, timeout=timeout)