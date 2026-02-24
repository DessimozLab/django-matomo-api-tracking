# -*- coding: utf-8 -*-
import logging
import responses
import json
from collections import ChainMap
from urllib.parse import parse_qs
from unittest.mock import patch, MagicMock
from requests.exceptions import Timeout
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.test.client import Client, RequestFactory
from django.conf import settings
from .middleware import MatomoApiTrackingMiddleware
from .utils import COOKIE_NAME, build_api_params
from .transport import logger as transport_logger
from .backends.redis_batch import RedisBatchTrackingBackend


class MatomoTestCase(TestCase):

    def make_fake_request(self, url, headers={}):
        """
        We don't have any normal views, so we're creating fake
        views using django's RequestFactory
        """

        def mock_view(request):
            return HttpResponse("")

        rf = RequestFactory()
        request = rf.get(url, **headers)
        session_middleware = SessionMiddleware(mock_view)
        session_middleware.process_request(request)
        request.session.save()
        return request

    @override_settings(
        MIDDLEWARE=[
            'django.contrib.sessions.middleware.SessionMiddleware',
            'matomo_api_tracking.middleware.MatomoApiTrackingMiddleware'
        ],
        TASK_ALWAYS_EAGER=True,
        BROKER_URL='memory://')
    @responses.activate
    def test_matomo_middleware(self):
        responses.add(
            responses.GET, settings.MATOMO_API_TRACKING['url'],
            body='',
            status=200)

        headers = {'HTTP_X_IORG_FBS_UIP': '100.100.200.10'}
        request = self.make_fake_request(
            '/sections/deep-soul/ما-مدى-جاهزيتك-للإنترنت/', headers)

        html = ("<html><head><title>"
                "ما-مدى-جاهزيتك-للإنترنت</title></head></html>")
        middleware = MatomoApiTrackingMiddleware(lambda r: HttpResponse(html))
        response = middleware(request)
        uid = response.cookies.get(COOKIE_NAME).value

        self.assertEqual(len(responses.calls), 1)

        track_url = responses.calls[0].request.url

        self.assertEqual(
            parse_qs(track_url).get('url'), [
                'http://testserver/sections/deep-soul/%D9%85%D8%A7-%D9%85%D8%AF%D9%89-'
                '%D8%AC%D8%A7%D9%87%D8%B2%D9%8A%D8%AA%D9%83-%D9%84%D9'
                '%84%D8%A5%D9%86%D8%AA%D8%B1%D9%86%D8%AA/'])
        self.assertEqual(parse_qs(track_url).get('action_name'), ['ما-مدى-جاهزيتك-للإنترنت'])
        self.assertEqual(parse_qs(track_url).get('idsite'),
                         [str(settings.MATOMO_API_TRACKING['site_id'])])
        self.assertEqual(parse_qs(track_url).get('_id'), [uid])
        self.assertEqual(len(uid), 16)
        self.assertIsNone(parse_qs(track_url).get('cip'))

    @override_settings(
        MIDDLEWARE=[
            'django.contrib.sessions.middleware.SessionMiddleware',
            'matomo_api_tracking.middleware.MatomoApiTrackingMiddleware'
        ],
        TASK_ALWAYS_EAGER=True,
        BROKER_URL='memory://')
    @responses.activate
    def test_build_api_params_for_title(self):
        responses.add(
            responses.GET, settings.MATOMO_API_TRACKING['url'],
            body='',
            status=200)

        headers = {
            'HTTP_X_IORG_FBS_UIP': '100.100.200.10',
            'HTTP_X_DCMGUID': '0000-0000-0000-0000'}
        request = self.make_fake_request(
            '/sections/deep-soul/ما-مدى-جاهزيتك-للإنترنت/', headers)

        html = "<html><head><title>title</title></head></html>"
        middleware = MatomoApiTrackingMiddleware(lambda r: HttpResponse(html))
        response = middleware(request)

        api_dict = build_api_params(
            request, 'ua-test-id', '/some/path/',
            referer='/some/path/', title='ما-مدى-جاهزيتك-للإنترنت')
        self.assertEqual(api_dict['matomo_params'].get('action_name'), 'ما-مدى-جاهزيتك-للإنترنت')
        self.assertIsNotNone(response)

    @responses.activate
    def test_build_api_params_for_user_id(self):
        request = self.make_fake_request('/somewhere/')

        api_dict_without_uid = build_api_params(
            request, 'ua-test-id', '/some/path/', )

        api_dict_with_uid = build_api_params(
            request, 'ua-test-id', '/some/path/', user_id='402-3a6')

        self.assertEqual(
            api_dict_without_uid['matomo_params'].get('uid'), None)
        self.assertEqual(
            api_dict_with_uid['matomo_params'].get('uid'), '402-3a6')

    @responses.activate
    def test_build_api_params_for_direct_referals(self):
        headers = {'HTTP_HOST': 'localhost:8000'}
        request = self.make_fake_request('/somewhere/', headers)
        api_dict_without_referal = build_api_params(
            request, 'ua-test-id', '/some/path/', )
        api_dict_without_direct_referal = build_api_params(
            request, 'ua-test-id', '/some/path/',
            referer='http://test.com/some/path/')

        api_dict_with_direct_referal = build_api_params(
            request, 'ua-test-id', '/some/path/',
            referer='http://localhost:8000/some/path/')

        # None: if referal is not set
        self.assertEqual(
            api_dict_without_referal['matomo_params']['urlref'], '')
        # Include referals from another host
        self.assertEqual(
            api_dict_without_direct_referal['matomo_params']['urlref'],
            'http://test.com/some/path/')
        # Exlcude referals from the same host
        self.assertEqual(
            api_dict_with_direct_referal['matomo_params']['urlref'],
            'http://localhost:8000/some/path/')

    @responses.activate
    def test_build_api_params_for_custom_params(self):
        request = self.make_fake_request('/somewhere/')

        api_dict_without_custom = build_api_params(
            request, 'ua-test-id', '/some/path/', )

        api_dict_with_custom = build_api_params(
            request, 'ua-test-id', '/some/path/',
            custom_params={'key': 'value'})

        self.assertEqual(
            api_dict_without_custom['matomo_params'].get('key'), None)
        self.assertEqual(
            api_dict_with_custom['matomo_params'].get('key'), 'value')

    @override_settings(MIDDLEWARE=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        'matomo_api_tracking.middleware.MatomoApiTrackingMiddleware'
    ])
    @responses.activate
    def test_matomo_middleware_no_title(self):
        responses.add(
            responses.GET, settings.MATOMO_API_TRACKING['url'],
            body='',
            status=200)

        headers = {'HTTP_X_IORG_FBS_UIP': '100.100.200.10'}
        request = self.make_fake_request('/somewhere/', headers)

        middleware = MatomoApiTrackingMiddleware(lambda req: HttpResponse())
        response = middleware(request)
        uid = response.cookies.get(COOKIE_NAME).value

        # check tracking request sent to server
        self.assertEqual(len(responses.calls), 1)

        track_url = responses.calls[0].request.url

        self.assertEqual(parse_qs(track_url).get('url'), ['http://testserver/somewhere/'])
        self.assertEqual(parse_qs(track_url).get('action_name'), None)
        self.assertEqual(parse_qs(track_url).get('idsite'),
                         [str(settings.MATOMO_API_TRACKING['site_id'])])
        self.assertEqual(parse_qs(track_url).get('_id'), [uid])
        self.assertEqual(len(uid), 16)
        self.assertIsNone(parse_qs(track_url).get('cip'))

    @override_settings(MIDDLEWARE=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        'matomo_api_tracking.middleware.MatomoApiTrackingMiddleware'
    ], MATOMO_API_TRACKING=ChainMap({'token_auth': ['33dc3f2536d3025974cccb4b4d2d98f4']},
                                    settings.MATOMO_API_TRACKING))
    def test_matomo_middleware_sends_cip_with_token_auth(self):
        @responses.activate
        def test_matomo_middleware_no_title(self):
            responses.add(
                responses.GET, settings.MATOMO_API_TRACKING['url'],
                body='',
                status=200)

            headers = {'HTTP_X_IORG_FBS_UIP': '100.100.200.10'}
            request = self.make_fake_request('/somewhere/', headers)

            middleware = MatomoApiTrackingMiddleware(lambda req: HttpResponse())
            response = middleware(request)
            uid = response.cookies.get(COOKIE_NAME).value

            # check tracking request sent to server
            self.assertEqual(len(responses.calls), 1)

            track_url = responses.calls[0].request.url

            self.assertEqual(parse_qs(track_url).get('url'), ['http://testserver/somewhere/'])
            self.assertEqual(parse_qs(track_url).get('action_name'), None)
            self.assertEqual(parse_qs(track_url).get('idsite'),
                             [str(settings.MATOMO_API_TRACKING['site_id'])])
            self.assertEqual(parse_qs(track_url).get('_id'), [uid])
            self.assertEqual(len(uid), 16)
            self.assertEqual(parse_qs(track_url).get('cip'), ['100.100.200.10'])

    @override_settings(MIDDLEWARE=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        'matomo_api_tracking.middleware.MatomoApiTrackingMiddleware'
    ], MATOMO_API_TRACKING=ChainMap({'ignore_paths': ['/ignore-this']},
                                    settings.MATOMO_API_TRACKING))
    def test_matomo_middleware_ignore_path(self):
        request = self.make_fake_request('/ignore-this/somewhere/')
        middleware = MatomoApiTrackingMiddleware(lambda req: HttpResponse())
        middleware(request)
        self.assertEqual(len(responses.calls), 0)

    @override_settings(MIDDLEWARE=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        'matomo_api_tracking.middleware.MatomoApiTrackingMiddleware'
    ], MATOMO_API_TRACKING={})
    def test_matomo_middleware_no_account_set(self):
        client = Client()
        with self.assertRaises(Exception):
            client.get('/home/?p=%2Fhome&r=test.com')

    @override_settings(MIDDLEWARE=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        'matomo_api_tracking.middleware.MatomoApiTrackingMiddleware'
    ], MATOMO_API_TRACKING=ChainMap({'timeout': "non-numeric-value"},
                                    settings.MATOMO_API_TRACKING))
    def test_matomo_middleware_non_numeric_timeout(self):
        client = Client()
        with self.assertRaises(Exception):
            client.get('/home/?p=%2Fhome&r=test.com')

    @responses.activate
    def test_sending_tracking_request_logs(self):
        request = self.make_fake_request('/somewhere/')
        responses.add(
            responses.GET, settings.MATOMO_API_TRACKING['url'],
            body='',
            status=200)
        middleware = MatomoApiTrackingMiddleware(lambda req: HttpResponse())
        with self.assertLogs(transport_logger, logging.DEBUG) as cm:
            middleware(request)
        self.assertIn("Matomo tracking sent successfully", cm.output[0])

    @responses.activate
    def test_sending_tracking_request_logs_failure_as_errors(self):
        request = self.make_fake_request('/somewhere/')
        responses.add(
            responses.GET, settings.MATOMO_API_TRACKING['url'],
            body='',
            status=400)
        middleware = MatomoApiTrackingMiddleware(lambda req: HttpResponse())
        with self.assertLogs(transport_logger, logging.WARNING) as cm:
            middleware(request)
        self.assertIn("Matomo tracking failed", cm.output[0])
        self.assertIn("Bad Request", cm.output[0])

    @patch('matomo_api_tracking.transport.logger')
    @patch('matomo_api_tracking.transport.requests.get')
    def test_send_matomo_tracking_logs_timeout(self, mock_get, mock_logger):
        from matomo_api_tracking.tasks import send_matomo_tracking
        mock_get.side_effect = Timeout
        params = {
            'user_agent': 'test-agent',
            'language': 'en'
        }
        matomo_url = 'http://example.com?foo=bar'
        send_matomo_tracking(params, {}, matomo_url, 1)
        mock_logger.warning.assert_any_call("tracking request timed out: %s", matomo_url)
        self.assertTrue(mock_logger.warning.called)


class RedisBatchTrackingBackendTests(TestCase):

    @patch('matomo_api_tracking.backends.redis_batch.redis')
    @patch('matomo_api_tracking.backends.redis_batch.settings')
    def test_send_pushes_to_redis_list(self, mock_settings, mock_redis_module):
        # Fake settings
        mock_settings.MATOMO_API_TRACKING = {
            'redis_url': 'redis://localhost:6379/0',
            'redis_key': 'matomo_test_events'
        }

        # Fake Redis connection and instance
        mock_redis_instance = MagicMock()
        mock_redis_module.Redis.from_url.return_value = mock_redis_instance

        backend = RedisBatchTrackingBackend()
        params = {'foo': 'bar'}
        meta = {'baz': 42}
        backend.send(params, meta)

        # Check that Redis rpush was called correctly
        mock_redis_instance.rpush.assert_called_once()
        called_key, called_value = mock_redis_instance.rpush.call_args[0]
        self.assertEqual(called_key, 'matomo_test_events')
        loaded = json.loads(called_value)
        self.assertEqual(loaded['params'], params)
        self.assertEqual(loaded['meta'], meta)

    @patch('matomo_api_tracking.backends.redis_batch.redis', None)
    def test_raises_if_redis_not_installed(self):
        with self.assertRaises(Exception) as cm:
            RedisBatchTrackingBackend()
        self.assertIn("Redis not installed", str(cm.exception))

    @patch('matomo_api_tracking.backends.redis_batch.redis')
    @patch('matomo_api_tracking.backends.redis_batch.settings')
    def test_key_defaults_if_not_set(self, mock_settings, mock_redis_module):
        # No redis_key in config
        mock_settings.MATOMO_API_TRACKING = {
            'redis_url': 'redis://localhost:6379/0',
        }
        mock_redis_instance = MagicMock()
        mock_redis_module.Redis.from_url.return_value = mock_redis_instance
        backend = RedisBatchTrackingBackend()
        self.assertEqual(backend.key, 'matomo_events')


class FlushMatomoBatchTests(TestCase):
    @patch('matomo_api_tracking.tasks.redis')
    @patch('matomo_api_tracking.tasks.send_bulk_tracking_events')
    @patch('matomo_api_tracking.tasks.settings')
    def test_flushes_events_and_calls_bulk_sender(self, mock_settings, mock_bulk, mock_redis_module):
        # Prepare fake settings and redis
        mock_settings.MATOMO_API_TRACKING = {
            'redis_url': 'redis://localhost/0',
            'url': 'http://example.com/track',
            'redis_key': 'matomo_events',
            'TOKEN_AUTH': 'abc',
        }

        mock_redis_instance = MagicMock()
        # Queue up two events, then None to break loop
        event_dicts = [
            {'params': {'foo': 1}, 'meta': {'u': 2}},
            {'params': {'bar': 3}, 'meta': {'u': 4}},
        ]
        mock_redis_instance.lpop.side_effect = [json.dumps(event_dicts[0]), json.dumps(event_dicts[1]), None]
        mock_redis_module.Redis.from_url.return_value = mock_redis_instance

        # Should indicate success
        mock_bulk.return_value = True

        from matomo_api_tracking.tasks import flush_matomo_batch
        flush_matomo_batch(batch_size=5)

        # Should read from redis for correct key
        mock_redis_instance.lpop.assert_any_call('matomo_events')
        # Should call the bulk event sender with decoded events
        mock_bulk.assert_called_once()
        sent_events, sent_url, sent_token, sent_timeout = mock_bulk.call_args[0]
        self.assertEqual(sent_events, event_dicts)
        self.assertEqual(sent_url, 'http://example.com/track')
        self.assertEqual(sent_token, 'abc')
        self.assertIsInstance(sent_timeout, float)

    @patch('matomo_api_tracking.tasks.redis')
    @patch('matomo_api_tracking.tasks.send_bulk_tracking_events')
    @patch('matomo_api_tracking.tasks.settings')
    def test_if_no_events_it_returns(self, mock_settings, mock_bulk, mock_redis_module):
        mock_settings.MATOMO_API_TRACKING = {
            'redis_url': 'redis://localhost/0',
            'url': 'http://example.com/track',
        }
        mock_redis_instance = MagicMock()
        mock_redis_instance.lpop.return_value = None
        mock_redis_module.Redis.from_url.return_value = mock_redis_instance

        from matomo_api_tracking.tasks import flush_matomo_batch
        flush_matomo_batch()
        mock_bulk.assert_not_called()  # No events, so bulk is not called

    @patch('matomo_api_tracking.tasks.redis', None)
    def test_raises_when_no_redis(self):
        from matomo_api_tracking.tasks import flush_matomo_batch
        with self.assertRaises(Exception) as cm:
            flush_matomo_batch()
        self.assertIn("Redis not installed", str(cm.exception))

    @patch('matomo_api_tracking.tasks.redis')
    @patch('matomo_api_tracking.tasks.send_bulk_tracking_events')
    @patch('matomo_api_tracking.tasks.settings')
    def test_failed_bulk_requeues_events(self, mock_settings, mock_bulk, mock_redis_module):
        # Prepare minimal config
        mock_settings.MATOMO_API_TRACKING = {
            'redis_url': 'redis://localhost',
            'url': 'http://example.com',
            'redis_key': 'matomo_events'
        }
        mock_redis_instance = MagicMock()
        event_dict = {'params': {'foo': 5}, 'meta': {'bar': 6}}
        mock_redis_instance.lpop.side_effect = [json.dumps(event_dict), None]
        mock_redis_module.Redis.from_url.return_value = mock_redis_instance
        # Fail the bulk sending
        mock_bulk.return_value = False

        from matomo_api_tracking.tasks import flush_matomo_batch
        with patch('matomo_api_tracking.tasks.logger') as mock_logger:
            flush_matomo_batch(batch_size=3)
            # Should log a warning about failure
            self.assertTrue(
                any("will be pushed back" in str(arg) \
                    for call_args in mock_logger.warning.call_args_list \
                    for arg in call_args[0]
                )
            )
        # Should requeue the event
        mock_redis_instance.lpush.assert_called_once_with('matomo_events', json.dumps(event_dict))

    @patch('matomo_api_tracking.tasks.redis')
    @patch('matomo_api_tracking.tasks.send_bulk_tracking_events')
    @patch('matomo_api_tracking.tasks.settings')
    def test_raises_on_missing_config(self, mock_settings, mock_bulk, mock_redis_module):
        mock_settings.MATOMO_API_TRACKING = {'url': '', 'redis_url': ''}
        mock_redis_instance = MagicMock()
        mock_redis_module.Redis.from_url.return_value = mock_redis_instance

        from matomo_api_tracking.tasks import flush_matomo_batch
        with self.assertRaises(Exception) as cm:
            flush_matomo_batch()
        self.assertIn("Matomo configuration incomplete", str(cm.exception))
