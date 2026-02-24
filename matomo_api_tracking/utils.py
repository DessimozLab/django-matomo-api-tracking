import hashlib
import time
import uuid
import random
from django.conf import settings
from django.utils.translation import get_language_from_request
from urllib.parse import urlencode, quote

VERSION = '1'
COOKIE_NAME = '__matomo'
COOKIE_PATH = '/'
COOKIE_USER_PERSISTENCE = 63072000   # 2years


def get_visitor_id(cookie, client_ip, request):
    """Generate a visitor id for this hit.
    If there is a visitor id in the cookie, use that, otherwise
    use the authenticated user or as a last resort the IP.
    """
    if cookie:
        return cookie
    if hasattr(request, 'user') and request.user.is_authenticated:
        # create the visitor id from the username
        cid = hashlib.md5(request.user.username.encode('utf-8')).hexdigest()
    elif client_ip:
        cid = hashlib.md5(client_ip.encode('utf-8')).hexdigest()
    else:
        # otherwise this is a new user, create a new random id.
        cid = str(uuid.uuid4())
    return cid[:16]


def set_cookie(params, response):
    COOKIE_USER_PERSISTENCE = params.get('COOKIE_USER_PERSISTENCE')
    COOKIE_PATH = params.get('COOKIE_PATH')
    visitor_id = params.get('visitor_id')

    time_tup = time.localtime(time.time() + COOKIE_USER_PERSISTENCE)

    # always try and add the cookie to the response
    response.set_cookie(
        COOKIE_NAME,
        value=visitor_id,
        expires=time.strftime('%a, %d-%b-%Y %H:%M:%S %Z', time_tup),
        path=COOKIE_PATH,
    )
    return response


def build_api_params(
        request, account, path=None, referer=None, title=None,
        user_id=None, custom_params=None):
    if custom_params is None:
        custom_params = {}

    meta = request.META
    # determine the referrer
    referer = referer or request.GET.get('r', '')

    custom_uip = None
    if hasattr(settings, 'CUSTOM_UIP_HEADER') and settings.CUSTOM_UIP_HEADER:
        custom_uip = meta.get(settings.CUSTOM_UIP_HEADER)
    path = path or request.GET.get('p', '/')
    path = request.build_absolute_uri(path)

    # get client ip address
    if 'HTTP_X_FORWARDED_FOR' in meta and meta.get('HTTP_X_FORWARDED_FOR', ''):
        client_ip = meta.get('HTTP_X_FORWARDED_FOR', '')
        if client_ip:
            # The values in a proxied environment are usually presented in the
            # following format:
            # X-Forwarded-For: client, proxy1, proxy2
            # In this case, we want the client IP Only
            client_ip = client_ip.split(',')[0]
    else:
        client_ip = meta.get('REMOTE_ADDR', '')

    user_agent = meta.get('HTTP_USER_AGENT') or meta.get('USER_AGENT', 'Unknown')

    # try and get visitor_id from cookie, or genereate one
    cookie = request.COOKIES.get(COOKIE_NAME)
    visitor_id = get_visitor_id(cookie, client_ip, request)

    # build the parameter collection
    params = {
        'apiv': VERSION,
        'idsite': account,
        'rec': 1,
        'rand': str(random.randint(0, 0x7fffffff)),
        '_id': visitor_id,
        'urlref': referer,
        'url': path,
        'cdt': int(time.time()),
        'ua': user_agent,
    }

    # add user ID if exists
    if user_id:
        params.update({'uid': user_id})

    # if token_auth is specified, we can add the cip parameter (visitor's IP)
    try:
        token_auth = settings.MATOMO_API_TRACKING['token_auth']
        params['cip'] = custom_uip or client_ip
    except KeyError:
        pass

    # add custom parameters
    params.update(custom_params)

    # add page title if supplied
    if title:
        if isinstance(title, bytes):
            title = title.decode('utf-8')
        params['action_name'] = title

    locale = get_language_from_request(request)
    if locale:
        params['lang'] = locale

    return {
        "matomo_params": params,
        "meta": {
            'user_agent': user_agent,
            'language': locale or settings.LANGUAGE_CODE,
            'visitor_id': visitor_id,
            'client_ip': client_ip,
            'COOKIE_USER_PERSISTENCE': COOKIE_USER_PERSISTENCE,
            'COOKIE_NAME': COOKIE_NAME,
            'COOKIE_PATH': COOKIE_PATH,
        }
    }
