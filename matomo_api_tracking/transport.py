import logging
import requests
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


def send_single_tracking_event(
    params: dict, meta: dict, matomo_url: str, timeout: float = 8, token_auth: str = None,
) -> bool:
    """
    Send a single tracking request to Matomo.

    Without a token_auth, sends a plain GET (Matomo only honors the 'ua'/'lang'
    override params and 'cip' when authenticated, so GET plus request headers is
    used in that case). With a token_auth configured, sends it as a POST using
    Matomo's bulk tracking request format instead, which keeps the token out of
    the URL/query string and works fine with a single event.
    """
    if token_auth:
        return send_bulk_tracking_events([{"params": params}], matomo_url, token_auth, timeout)

    headers = {
        "User-Agent": meta.get("user_agent", ""),
        "Accept-Language": meta.get("language", ""),
    }
    logger.debug("Sending Matomo tracking request to %s with params: %s", matomo_url, params)
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

    logger.debug(
        "Sending Matomo bulk tracking request to %s with %d event(s): %s",
        matomo_url, len(bulk_requests), bulk_requests,
    )
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