# Django Matomo API Tracking

This django app enables server side traffic tracking. The code is greatly inspired by the [Django Google Analytics](https://github.com/praekeltfoundation/django-google-analytics) app.

## Prerequisites

For this middleware to work you must have the following items configured:

1. A Matomo server to send tracking data to.
2. A
   [Celery task queue configured for Django](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html#using-celery-with-django)
   and functional for the middleware to use.  The task queue
   allows tracking data to be sent asynchronously. You will also need to install a broker of some
   kind for Celery to use. (i.e. RabbitMQ, Redis, etc.)


## Installation

1. Install ``django-matomo-api-tracking`` from pypi using ``pip install django-matomo-api-tracking``

## Setup / Configuration

1. Add ``matomo_api_tracking`` to your ``INSTALLED_APPS`` setting.
2. Add a new variable ``MATOMO_API_TRACKING`` to your settings to configure the behaviour of the app:

```
    MATOMO_API_TRACKING = {
        'url': 'https://your-matomo-server.com/matomo.php',
        'site_id': <your_site_id>,
        'backend': 
            # choose one of the following backends. if non is specified, the default to CeleryTrackingBackend
            "matomo_api_tracking.backends.celery.CeleryTrackingBackend",
            # "matomo_api_tracking.backends.redis_batch.RedisBatchTrackingBackend",
            # "matomo_api_tracking.backends.direct.DirectTrackingBackend",  # for debugging
        # 'ignore_paths': ["/debug/", "/health/"],
        # 'token_auth': "<your auth token>",  # e.g.  "33dc3f2536d3025974cccb4b4d2d98f4"
        # 'timeout': 8,
        # 'redis_url': 'redis://localhost:6379/0',  # only needed for batching in the RedisBatchTrackingBackend
        # 'redis_key': 'matomo_events',             # only needed for batching in the RedisBatchTrackingBackend
    }
    
```
The app supports multiple backends for sending the tracking data to the Matomo server. 
The **default backend** is the CeleryTrackingBackend, which requires you to have Celery 
set up in your project. The CeleryTrackingBackend sends every tracking event in a separate
celery task to the Matomo server. This is the recommended setup for production websites with
medium traffic.

Alternatively, for really low-traffic websites or developing purposes, you can use the
DirectTrackingBackend. There, no additional setup is required. The middleware sends the 
tracking data directly in the main thread to the Matomo server.

For **high-traffic websites**, you can also use the Redis with **RedisBatchTrackingBackend**. This backend 
has been implemented in version 0.3.0 to reduce the load on the Matomo server. Multiple django processes can
send tracking data to the Matomo server in parallel by using a Redis queue. In the celery configuation, you 
should enable a periodic task that runs every few seconds to send the tracking data in batches to the Matomo 
server. This way, you can reduce the number of requests to the Matomo server and improve the performance 
of your website.

If you don't want to use Celery, you can choose the Redis batch backend, which batches the tracking data and sends it to the Matomo server at regular intervals. For debugging purposes, you can also use the direct backend, which sends the tracking data directly to the Matomo server without any batching.

3. enable the middleware by adding the matomo_api_tracking middleware to the list of enabled middlewares in the settings: 

```
    MIDDLEWARE = [
        ...
        'matomo_api_tracking.middleware.MatomoApiTrackingMiddleware',
    ]
```

4. configure a periodic celery beat task if you want to use the RedisBatchTrackingBackend.

```
    CELERY_BEAT_SCHEDULE = {
        'flush-matomo-every-n-seconds': {
            'task': 'matomo_api_tracking.tasks.flush_matomo_batch',
            'schedule': 10.0,  # seconds
        },
    }
```
and make sure that the celery beat scheduler is running ( e.g. `celery --app <your_project_name> beat -l info`). 

In the settings part, the `ignore_path` can be used to entirely skip certain
paths from being tracked. If you specify an `token_auth`, the app will also send
the client's IP address (cip parameter). But this is not required. Additionally,
you can specify a timeout for the requests for middleware sent tracking data.


