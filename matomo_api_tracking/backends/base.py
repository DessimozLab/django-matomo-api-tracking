from django.conf import settings


class BaseTrackingBackend:
    """Base class for Matomo tracking backends."""

    def __init__(self):
        try:
            config = settings.MATOMO_API_TRACKING
            self.timeout = float(config.get("timeout", 8))
            self.url = config["url"]
        except KeyError:
            raise Exception("Matomo configuration incomplete")
        except ValueError:
            raise Exception("Matomo timeout must be a numeric value")

    def send(self, params: dict, meta: dict):
        raise NotImplementedError("Tracking backends must implement send()")