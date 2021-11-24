from mock import patch
from django.test import TestCase, Client
from django.test.utils import override_settings
from xff.middleware import XForwardedForMiddleware


class WebTestCase(TestCase):
    ''' Helpers for web request testing '''
    def assert_http_ok(self, response, message=None):
        ''' Assert response code 200 '''
        self.assertEqual(200, response.status_code, message)

    def assert_http_bad_request(self, response, message=None):
        ''' Assert response code 400 '''
        self.assertEqual(400, response.status_code, message)


class TestStrict(WebTestCase):
    def setUp(self):
        self.middleware = XForwardedForMiddleware()
        self.client = Client()
        self.patcher = patch('xff.middleware.logger', autospec=True)
        self.logger = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @override_settings(XFF_STRICT=True)
    def test_no_header(self):
        response = self.client.get('/')
        self.assert_http_bad_request(response)
        self.assertEqual(1, self.logger.error.call_count)

    @override_settings(XFF_STRICT=True)
    def test_no_header_exempt(self):
        response = self.client.get('/health/')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_STRICT=True, XFF_HEADER_REQUIRED=False)
    def test_no_header_not_required(self):
        response = self.client.get('/')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_HEADER_REQUIRED=False)
    def test_no_header_not_required_exempt(self):
        response = self.client.get('/health/')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_STRICT=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_few_proxies(self):
        response = self.client.get('/', HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assert_http_bad_request(response)
        self.assertEqual(1, self.logger.warning.call_count)

    @override_settings(XFF_STRICT=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_few_proxies_exempt(self):
        response = self.client.get('/health/',
                                   HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_STRICT=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_correct_proxies(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_STRICT=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False, XFF_EXEMPT_STEALTH=True)
    def test_correct_proxies_exempt_stealth(self):
        response = self.client.get(
            '/health/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2')
        self.assertEqual(404, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_STRICT=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_many_proxies(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assert_http_bad_request(response)
        self.assertEqual(1, self.logger.warning.call_count)

    @override_settings(XFF_STRICT=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_many_proxies_exempt(self):
        response = self.client.get(
            '/health/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_LOOSE_UNSAFE=True, XFF_STRICT=True,
                       XFF_TRUSTED_PROXY_DEPTH=2, XFF_HEADER_REQUIRED=True,
                       XFF_NO_SPOOFING=True, XFF_ALWAYS_PROXY=True)
    def test_loose_no_header(self):
        response = self.client.get('/')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_LOOSE_UNSAFE=True, XFF_STRICT=True,
                       XFF_TRUSTED_PROXY_DEPTH=2, XFF_HEADER_REQUIRED=True,
                       XFF_NO_SPOOFING=True, XFF_ALWAYS_PROXY=True)
    def test_loose(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assert_http_ok(response, 'Too few addresses')
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assert_http_ok(response, 'Correct addresses')
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assert_http_ok(response, 'Too many addresses')
        assert not self.logger.method_calls


class TestClean(WebTestCase):
    def setUp(self):
        self.middleware = XForwardedForMiddleware()
        self.client = Client()

    @override_settings(XFF_TRUSTED_PROXY_DEPTH=2)
    def test_too_many_proxies_rewrites_xff(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assert_http_ok(response)
        request = response.wsgi_request
        self.assertEqual('127.0.0.2,127.0.0.3',
                         request.META['HTTP_X_FORWARDED_FOR'])

    @override_settings(XFF_TRUSTED_PROXY_DEPTH=2, XFF_CLEAN=False)
    def test_can_be_disabled(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assert_http_ok(response)
        request = response.wsgi_request
        self.assertEqual('127.0.0.1, 127.0.0.2, 127.0.0.3',
                         request.META['HTTP_X_FORWARDED_FOR'])


class TestRewriteRemote(WebTestCase):
    def setUp(self):
        self.middleware = XForwardedForMiddleware()
        self.client = Client()

    @override_settings(XFF_TRUSTED_PROXY_DEPTH=2)
    def test_rewrites_remote_addr(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.3, 127.0.0.2',
            REMOTE_ADDR='127.0.0.9',
        )
        self.assert_http_ok(response)
        request = response.wsgi_request
        self.assertEqual('127.0.0.3',
                         request.META['REMOTE_ADDR'])

    @override_settings(XFF_TRUSTED_PROXY_DEPTH=2, XFF_REWRITE_REMOTE_ADDR=False)
    def test_can_be_disabled(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.3, 127.0.0.2',
            REMOTE_ADDR='127.0.0.9',
        )
        self.assert_http_ok(response)
        request = response.wsgi_request
        self.assertEqual('127.0.0.9', request.META['REMOTE_ADDR'])


class TestProxyDepth(WebTestCase):
    def setUp(self):
        self.middleware = XForwardedForMiddleware()
        self.client = Client()
        self.patcher = patch('xff.middleware.logger', autospec=True)
        self.logger = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @override_settings(XFF_TRUSTED_PROXY_DEPTH=2)
    def test_too_many_proxies_logs_spoof_attempt(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assert_http_ok(response)
        expected_message = (
            'X-Forwarded-For spoof attempt with 3 addresses when 2 expected. '
            'Full header: 127.0.0.1, 127.0.0.2, 127.0.0.3'
        )
        self.logger.info.assert_called_once_with(expected_message)



class TestNoSpoofing(WebTestCase):
    def setUp(self):
        self.middleware = XForwardedForMiddleware()
        self.client = Client()
        self.patcher = patch('xff.middleware.logger', autospec=True)
        self.logger = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @override_settings(XFF_NO_SPOOFING=True)
    def test_no_header(self):
        response = self.client.get('/')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_NO_SPOOFING=True, XFF_TRUSTED_PROXY_DEPTH=2)
    def test_too_few_proxies(self):
        response = self.client.get('/', HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assert_http_ok(response)
        self.assertEqual(1, self.logger.warning.call_count)
        self.assertEqual(1, len(self.logger.method_calls))

    @override_settings(XFF_NO_SPOOFING=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_few_proxies_exempt(self):
        response = self.client.get('/health/',
                                   HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_NO_SPOOFING=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_correct_proxies(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_NO_SPOOFING=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_many_proxies(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assert_http_bad_request(response)
        self.assertEqual(1, self.logger.info.call_count)
        self.assertEqual(1, len(self.logger.method_calls))

    @override_settings(XFF_NO_SPOOFING=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_many_proxies_exempt(self):
        response = self.client.get(
            '/health/', HTTP_REMOTE_ADDR='',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assert_http_ok(response)
        assert not self.logger.method_calls


class TestAlwaysProxy(WebTestCase):
    def setUp(self):
        self.middleware = XForwardedForMiddleware()
        self.client = Client()
        self.patcher = patch('xff.middleware.logger', autospec=True)
        self.logger = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @override_settings(XFF_ALWAYS_PROXY=True)
    def test_no_header(self):
        response = self.client.get('/')
        self.assert_http_bad_request(response)
        self.assertEqual(1, self.logger.error.call_count)

    @override_settings(XFF_ALWAYS_PROXY=True)
    def test_no_header_exempt(self):
        response = self.client.get('/health/')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_HEADER_REQUIRED=False)
    def test_no_header_not_required(self):
        response = self.client.get('/')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_HEADER_REQUIRED=False)
    def test_no_header_not_required_exempt(self):
        response = self.client.get('/health/')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_few_proxies(self):
        response = self.client.get('/', HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assert_http_bad_request(response)
        self.assertEqual(1, self.logger.warning.call_count)

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_few_proxies_exempt(self):
        response = self.client.get('/health/',
                                   HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_correct_proxies(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2')
        self.assert_http_ok(response)
        assert not self.logger.method_calls

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_many_proxies(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assert_http_ok(response)
        self.assertEqual(1, self.logger.info.call_count)

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_many_proxies_exempt(self):
        response = self.client.get(
            '/health/', HTTP_REMOTE_ADDR='',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assert_http_ok(response)
        assert not self.logger.method_calls
