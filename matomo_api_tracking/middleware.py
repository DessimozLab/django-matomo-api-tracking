from django.conf import settings
from .tasks import send_matomo_tracking
from bs4 import BeautifulSoup
import logging

from .utils import build_api_params, set_cookie
from .dispatcher import get_backend

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
            _ = settings.MATOMO_API_TRACKING['url']
            account = settings.MATOMO_API_TRACKING['site_id']
            ignore_paths = settings.MATOMO_API_TRACKING.get('ignore_paths', [])
        except (AttributeError, KeyError):
            raise Exception("Matomo configuration incomplete")

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

        referer = request.META.get('HTTP_REFERER', None)
        user_id = None
        if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
            user_id = getattr(request.user, 'id', None)

        data = build_api_params(
            request, account, path=request.path, referer=referer, title=title, user_id=user_id)
        params, meta = data['matomo_params'], data['meta']
        response = set_cookie(meta, response)
        backend = get_backend()
        backend.send(params, meta)

        return response
