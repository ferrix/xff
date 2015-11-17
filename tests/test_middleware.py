from mock import patch
from django.test import TestCase, Client
from django.test.utils import override_settings
from xff.middleware import XForwardedForMiddleware


class TestStrict(TestCase):
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
        self.assertEquals(400, response.status_code)
        self.assertEquals(1, self.logger.error.call_count)

    @override_settings(XFF_STRICT=True)
    def test_no_header_exempt(self):
        response = self.client.get('/health/')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_STRICT=True, XFF_HEADER_REQUIRED=False)
    def test_no_header_not_required(self):
        response = self.client.get('/')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_HEADER_REQUIRED=False)
    def test_no_header_not_required_exempt(self):
        response = self.client.get('/health/')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_STRICT=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_few_proxies(self):
        response = self.client.get('/', HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assertEquals(400, response.status_code)
        self.assertEquals(1, self.logger.warning.call_count)

    @override_settings(XFF_STRICT=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_few_proxies_exempt(self):
        response = self.client.get('/health/', HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_STRICT=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_correct_proxies(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_STRICT=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False, XFF_EXEMPT_STEALTH=True)
    def test_correct_proxies_exempt_stealth(self):
        response = self.client.get(
            '/health/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2')
        self.assertEquals(404, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_STRICT=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_many_proxies(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assertEquals(400, response.status_code)
        self.assertEquals(1, self.logger.warning.call_count)

    @override_settings(XFF_STRICT=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_many_proxies_exempt(self):
        response = self.client.get(
            '/health/', HTTP_REMOTE_ADDR='',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls


class TestNoSpoofing(TestCase):
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
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_NO_SPOOFING=True, XFF_TRUSTED_PROXY_DEPTH=2)
    def test_too_few_proxies(self):
        response = self.client.get('/', HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assertEquals(200, response.status_code)
        self.assertEquals(1, self.logger.warning.call_count)
        self.assertEquals(1, len(self.logger.method_calls))

    @override_settings(XFF_NO_SPOOFING=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_few_proxies_exempt(self):
        response = self.client.get('/health/', HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_NO_SPOOFING=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_correct_proxies(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_NO_SPOOFING=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_many_proxies(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assertEquals(400, response.status_code)
        self.assertEquals(1, self.logger.info.call_count)
        self.assertEquals(1, len(self.logger.method_calls))

    @override_settings(XFF_NO_SPOOFING=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_many_proxies_exempt(self):
        response = self.client.get(
            '/health/', HTTP_REMOTE_ADDR='',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls


class TestAlwaysProxy(TestCase):
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
        self.assertEquals(400, response.status_code)
        self.assertEquals(1, self.logger.error.call_count)

    @override_settings(XFF_ALWAYS_PROXY=True)
    def test_no_header_exempt(self):
        response = self.client.get('/health/')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_HEADER_REQUIRED=False)
    def test_no_header_not_required(self):
        response = self.client.get('/')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_HEADER_REQUIRED=False)
    def test_no_header_not_required_exempt(self):
        response = self.client.get('/health/')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_few_proxies(self):
        response = self.client.get('/', HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assertEquals(400, response.status_code)
        self.assertEquals(1, self.logger.warning.call_count)

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_few_proxies_exempt(self):
        response = self.client.get('/health/', HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_correct_proxies(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_many_proxies(self):
        response = self.client.get(
            '/',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assertEquals(200, response.status_code)
        self.assertEquals(1, self.logger.info.call_count)

    @override_settings(XFF_ALWAYS_PROXY=True, XFF_TRUSTED_PROXY_DEPTH=2,
                       XFF_HEADER_REQUIRED=False)
    def test_too_many_proxies_exempt(self):
        response = self.client.get(
            '/health/', HTTP_REMOTE_ADDR='',
            HTTP_X_FORWARDED_FOR='127.0.0.1, 127.0.0.2, 127.0.0.3')
        self.assertEquals(200, response.status_code)
        assert not self.logger.method_calls
