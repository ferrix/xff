import logging
from re import compile

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseNotFound

XFF_EXEMPT_URLS = []
if hasattr(settings, 'XFF_EXEMPT_URLS'):
    XFF_EXEMPT_URLS = [compile(expr) for expr in settings.XFF_EXEMPT_URLS]

logger = logging.getLogger(__name__)


class XForwardedForMiddleware(object):
    '''
    Fix HTTP_REMOTE_ADDR header to show client IP in a proxied environment.

    WARNING: If you are going to trust the address, you need to know how
    many proxies you have in chain. Nothing stops a malicious client from
    sending one and your reverse proxies adding one.

    You can set the exact number of reverse proxies by adding the
    XFF_TRUSTED_PROXY_DEPTH setting. Without it, the header will remain
    insecure even with this middleware. Setting XFF_STRICT = True will
    cause a bad request to be sent on spoofed or wrongly routed requests.
    XFF_ALWAYS_PROXY will drop all requests with too little depth.
    XFF_NO_SPOOFING will drop connections with too many headers.

    This middleware will automatically clean the X-Forwarded-For header
    unless XFF_CLEAN = False is set.

    XFF_LOOSE_UNSAFE = True will simply shut up and set the last in the
    stack.

    XFF_EXEMPT_URLS can be an iterable (eg. list) that defines URLs as
    regexps that will not be checked. XFF_EXEMPT_STEALTH = True will
    return a 404 when all proxies are present. This is nice for a
    healtcheck URL that is not for the public eye.

    XFF_HEADER_REQUIRED = True will return a bad request when the header
    is not set. By default it takes the same value as XFF_ALWAYS_PROXY.
    '''
    def process_request(self, request):
        path = request.path_info
        depth = getattr(settings, 'XFF_TRUSTED_PROXY_DEPTH', 0)
        exempt = any(m.match(path) for m in XFF_EXEMPT_URLS)
        stealth = getattr(settings, 'XFF_EXEMPT_STEALTH', False)
        loose = getattr(settings, 'XFF_LOOSE_UNSAFE', False)
        strict = getattr(settings, 'XFF_STRICT', False)
        always_proxy = getattr(settings, 'XFF_ALWAYS_PROXY', False)
        no_spoofing = getattr(settings, 'XFF_NO_SPOOFING', False)
        header_required = getattr(settings, 'XFF_HEADER_REQUIRED',
                                  (always_proxy or strict))
        clean = getattr(settings, 'XFF_CLEAN', True)

        if 'HTTP_X_FORWARDED_FOR' in request.META:
            header = request.META['HTTP_X_FORWARDED_FOR']
            levels = [x.strip() for x in header.split(',')]

            if len(levels) >= depth and exempt and stealth:
                return HttpResponseNotFound()

            if loose or exempt:
                request['HTTP_REMOTE_ADDR'] = levels[0]
                return None

            if len(levels) != depth and strict:
                logger.warning((
                    "Incorrect proxy depth in incoming request.\n" +
                    'Expected {} and got {} remote addresses in ' +
                    'X-Forwarded-For header.')
                    .format(
                        depth, len(levels)))
                return HttpResponseBadRequest()

            if len(levels) < depth or depth == 0:
                logger.warning(
                    'Not running behind as many reverse proxies as expected.\n' +
                    'The right value for XFF_TRUSTED_PROXY_DEPTH for this ' +
                    'request is {} and {} is configured.'.format(
                        len(levels), depth)
                )
                if always_proxy:
                    return HttpResponseBadRequest()

                depth = len(levels)
            elif len(levels) > depth:
                logger.info(
                    ('X-Forwarded-For spoof attempt with {} addresses when ' +
                     '{} expected. Full header: {}').format(
                         len(levels), depth, header))
                if no_spoofing:
                    return HttpResponseBadRequest()

            request.META['REMOTE_ADDR'] = levels[-1 * depth]

            if clean:
                cleaned = ','.join(levels[-1 * depth:])
                request.META['HTTP_X_FORWARDED_FOR'] = cleaned

        elif header_required and not exempt:
            logger.error(
                'No X-Forwarded-For header set, not behind a reverse proxy.')
            return HttpResponseBadRequest()

        return None
