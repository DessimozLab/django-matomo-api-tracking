import logging
import requests
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


def send_single_tracking_event(params: dict, meta: dict, matomo_url: str, timeout: float = 8) -> bool:
    """
    Send a single tracking request to Matomo using GET.
    Returns True on success.
    """
    headers = {
        "User-Agent": meta.get("user_agent", ""),
        "Accept-Language": meta.get("language", ""),
    }
    try:
        resp = requests.get(matomo_url, params=params, headers=headers, timeout=timeout)
        if resp.ok:
            logger.debug("Matomo tracking sent successfully.")
        else:
            logger.warning("Matomo tracking failed: %s", resp.reason)
        return resp.ok
    except requests.exceptions.Timeout:
        logger.warning("tracking request timed out: %s", matomo_url)
    except requests.RequestException as exc:
        logger.warning("Matomo tracking error: %s", exc)
    return False


def send_bulk_tracking_events(
    events: list,
    matomo_url: str,
    token: str,
    timeout: float = 8,
) -> bool:
    """
    Send multiple tracking events using Matomo bulk API.
    Expects events as list of dicts with 'params'.
    """
    bulk_requests = [
        "?" + urlencode(event["params"])
        for event in events
    ]

    try:
        resp = requests.post(
            matomo_url,
            json={"requests": bulk_requests, "token_auth": token},
            timeout=timeout,
        )

        if resp.ok:
            logger.debug("Matomo bulk tracking sent successfully.")
            return True

        logger.warning("Matomo bulk tracking failed: %s", resp.reason)
        return False

    except requests.RequestException as exc:
        logger.warning("Matomo bulk tracking error: %s", exc)
        return False