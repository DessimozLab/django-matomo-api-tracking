import logging
from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

_backend_instance = None


def get_backend():
    """Return singleton backend instance based on settings."""
    global _backend_instance
    if _backend_instance:
        return _backend_instance

    config = settings.MATOMO_API_TRACKING
    backend_path = config.get(
        "backend",
        "matomo_api_tracking.backends.celery.CeleryTrackingBackend"
    )

    backend_class = import_string(backend_path)
    logger.debug("Matomo tracking backend resolved to %s", backend_path)
    _backend_instance = backend_class()
    return _backend_instance