# Django Matomo API Tracking

This django app enables server side traffic tracking. The code is greatly inspired by the [Django Google Analytics](https://github.com/praekeltfoundation/django-google-analytics) app.

## Installation

1. Install ``django-matomo-api-tracking`` from pypi using ``pip install django-matomo-api-tracking``

## Setup / Configuration

1. add ``matomo_api_tracking`` to your ``INSTALLED_APPS`` setting.
2. add a new variable ``MATOMO_API_TRACKING`` to your settings to configure the behaviour of the app:


    MATOMO_API_TRACKING = {
        'url': 'https://your-matomo-server.com/matomo.php',
        'site_id': <your_site_id>,
        # 'ignore_paths': ["/debug/", "/health/"],
        # 'token_auth': "<your auth token>",  # e.g.  "33dc3f2536d3025974cccb4b4d2d98f4"
        # 'timeout': 8,
    }

3. enable the middleware by adding the matomo_api_tracking middleware to the list of enabled middlewares in the settings: 


    MIDDLEWARE = [
        ...
        'matomo_api_tracking.middleware.MatomoApiTrackingMiddleware',
    ]

In the settings part, the `ignore_path` can be used to entirely skip certain
paths from being tracked. If you specify an `token_auth`, the app will also send
the client's IP address (cip parameter). But this is not required. Additionally,
you can specify a timeout for the requests for middleware sent tracking data.
