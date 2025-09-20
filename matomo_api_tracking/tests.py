# -*- coding: utf-8 -*-
import logging
import responses
from collections import ChainMap
from urllib.parse import parse_qs
from unittest.mock import patch
from requests.exceptions import Timeout
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.test.client import Client, RequestFactory
from django.conf import settings
from .middleware import MatomoApiTrackingMiddleware
from .utils import COOKIE_NAME, build_api_params
from .tasks import logger as task_logger


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
        self.assertEqual(parse_qs(track_url).get('action_name'), [
            '%D9%85%D8%A7-%D9%85%D8%AF%D9%89-%D8%AC%D8%A7%D9%87%D8%B2%D9%8A%D8'
            '%AA%D9%83-%D9%84%D9%84%D8%A5%D9%86%D8%AA%D8%B1%D9%86%D8%AA'])
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
    def test_build_api_params_for_title_encoding(self):
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
        self.assertEqual(parse_qs(api_dict.get('url')).get('action_name'), [
            '%D9%85%D8%A7-%D9%85%D8%AF%D9%89-%D8%AC%D8%A7%D9%87%D8%B2%D9%8A%D8'
            '%AA%D9%83-%D9%84%D9%84%D8%A5%D9%86%D8%AA%D8%B1%D9%86%D8%AA'])
        self.assertIsNotNone(response)

    @responses.activate
    def test_build_api_params_for_user_id(self):
        request = self.make_fake_request('/somewhere/')

        api_dict_without_uid = build_api_params(
            request, 'ua-test-id', '/some/path/', )

        api_dict_with_uid = build_api_params(
            request, 'ua-test-id', '/some/path/', user_id='402-3a6')

        self.assertEqual(
            parse_qs(api_dict_without_uid.get('url')).get('uid'), None)
        self.assertEqual(
            parse_qs(api_dict_with_uid.get('url')).get('uid'), ['402-3a6'])

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
            parse_qs(api_dict_without_referal.get('url')).get('urlref'), None)
        # Include referals from another host
        self.assertEqual(
            parse_qs(
                api_dict_without_direct_referal.get('url')).get('urlref'),
            ['http://test.com/some/path/'])
        # Exlcude referals from the same host
        self.assertEqual(
            parse_qs(
                api_dict_with_direct_referal.get('url')).get('urlref'),
            ['http://localhost:8000/some/path/'])

    @responses.activate
    def test_build_api_params_for_custom_params(self):
        request = self.make_fake_request('/somewhere/')

        api_dict_without_custom = build_api_params(
            request, 'ua-test-id', '/some/path/', )

        api_dict_with_custom = build_api_params(
            request, 'ua-test-id', '/some/path/',
            custom_params={'key': 'value'})

        self.assertEqual(
            parse_qs(api_dict_without_custom.get('url')).get('key'), None)
        self.assertEqual(
            parse_qs(api_dict_with_custom.get('url')).get('key'), ['value'])

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
        with self.assertLogs(task_logger, logging.DEBUG) as cm:
            middleware(request)
        self.assertIn("successfully sent tracking request", cm.output[0])

    @responses.activate
    def test_sending_tracking_request_logs_failure_as_errors(self):
        request = self.make_fake_request('/somewhere/')
        responses.add(
            responses.GET, settings.MATOMO_API_TRACKING['url'],
            body='',
            status=400)
        middleware = MatomoApiTrackingMiddleware(lambda req: HttpResponse())
        with self.assertLogs(task_logger, logging.WARNING) as cm:
            middleware(request)
        self.assertIn("sending tracking request failed:", cm.output[0])
        self.assertIn("Bad Request", cm.output[0])
        self.assertIn("/somewhere/", cm.output[1])

    @patch('matomo_api_tracking.tasks.logger')
    @patch('matomo_api_tracking.tasks.requests.get')
    def test_send_matomo_tracking_logs_timeout(self, mock_get, mock_logger):
        from matomo_api_tracking.tasks import send_matomo_tracking
        mock_get.side_effect = Timeout
        params = {
            'url': 'http://example.com?foo=bar',
            'user_agent': 'test-agent',
            'language': 'en'
        }
        send_matomo_tracking(params)
        mock_logger.warning.assert_any_call("tracking request timed out: http://example.com?foo=bar")
        self.assertTrue(mock_logger.warning.called)