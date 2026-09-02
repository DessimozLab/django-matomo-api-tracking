from ..transport import send_single_tracking_event
from .base import BaseTrackingBackend


class DirectTrackingBackend(BaseTrackingBackend):
    """Send immediately (no Celery), useful for testing."""
    def send(self, params, meta):
        send_single_tracking_event(params, meta, self.url, self.timeout)
