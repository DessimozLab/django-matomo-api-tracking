from django.conf import settings
from .tasks import send_matomo_tracking
from bs4 import BeautifulSoup
import logging

from .utils import build_api_params, set_cookie

logger = logging.getLogger(__name__)


class MatomoApiTrackingMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response = self.process_response(request, response)
        return response

    def process_response(self, request, response):
        try:
            account = settings.MATOMO_API_TRACKING['site_id']
            ignore_paths = settings.MATOMO_API_TRACKING.get('ignore_paths', [])
            timeout = float(settings.MATOMO_API_TRACKING.get("timeout", 8))
        except (AttributeError, KeyError):
            raise Exception("Matomo configuration incomplete")
        except ValueError:
            raise Exception("Matomo timeout must be a numeric value")

        # do not log pages that start with an ignore_path url
        if any(p for p in ignore_paths if request.path.startswith(p)):
            return response

        try:
            if (response.content[:100].lower().find(b"<html>") >= 0 or
                    response.accepted_media_type == "text/html"):
                title = BeautifulSoup(
                    response.content, "html.parser").html.head.title.text
            else:
                title = None
        except AttributeError:
            title = None

        referer = request.META.get('HTTP_REFERER', '')
        params = build_api_params(
            request, account, path=request.path, referer=referer, title=title)
        response = set_cookie(params, response)
        try:
            send_matomo_tracking.delay(params, timeout=timeout)
        except Exception as e:
            logger.warning("cannot send google analytic tracking post: {}"
                           .format(e))

        return response
