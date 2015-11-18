Django X-Forwarded-For Properly
-------------------------------

The X-Forwarded-For header is used by many reverse proxies to pass the
IP addresses of the whole chain of hosts between client and application
server. The header looks something like this::

    X-Forwarded-For: 54.12.13.14, 192.168.2.0, 192.168.3.1

This translates to::

    X-Forwarded-For: client, proxy1[, proxy2[...]]

However it is just a header. Most default configurations simply append
to the header. It is trivial for a malicious client to deliver a header
in the initial request::

    X-Forwarded-For: phony, client

What ``django-xff`` does
========================

This library provides a decent and configurable middleware to rewrite
the ``request.META['HTTP_REMOTE_ADDR']`` to the correct client IP.

This is done by setting a depth of reverse proxies to be trusted alone.
The ``X-Forwarded-For`` header will additionally be sanitized from any
extraneous entries.

By default, if the expected depth of proxies is 3, the ``client``
address will be used in all of these examples::

    X-Forwarded-For: phony, client, proxy1, proxy2
    X-Forwarded-For: client, proxy1, proxy2
    X-Forwarded-For: client, proxy

Note:

 * Less proxies than expected is allowed by default, for varying lengths
   of proxy chains, the longest is the only one that can be trusted.
 * No header set is allowed by default and the library does nothing.

What ``django-xff`` does not do
===============================

This library does not check the IP addresses of any proxies along the
path of the message.

This library is unable to detect compromised proxies or any incoming
requests that have the right number addresses in the correct header.

TODO
====

 * Separate middleware that checks CIDR for the trusted proxies
 * Separate middleware that checks exact IP addresses for proxies

Configuration
=============

Add the following to your Django ``settings.py`` module to enable this
middleware for two reverse proxies expected. The middlewares are
processed order of appearance. This middleware should go somewhere
near the top to avoid giving a potentially malicious user chances to
validate passwords with malformed requests::

    MIDDLEWARE_CLASSES = [
       <a few middlewares here>
       'xff.middleware.XForwardedForMiddleware',
       <more middlewares here>
    ]

    XFF_TRUSTED_PROXY_DEPTH = 2

By default, no attempts are denied. There are several settings to send
a ``400`` (Bad Request) response to failing requests. Strict mode will
stop all failing requests::

    XFF_STRICT = True

To prevent only the clearly malicious requests, use the following
instead::

    XFF_NO_SPOOFING = True

To prevent requests that do not come through enough proxies, use the
following::

    XFF_ALWAYS_PROXY = True

The previous setting implies a Bad Request when there is no
``X-Forwarded-For`` header present. The following setting follows the
``XFF_ALWAYS_PROXY`` and ``XFF_STRICT`` by default but can be set
independently::

    XFF_HEADER_REQUIRED = False

Even in ``XFF_LOOSE_UNSAFE`` mode this will require the header::

    XFF_LOOSE_UNSAFE = True

For an unsafe setting, in development possibly, you can trust that the
first entry is always correct and still get the assumed client IP in
the right place, use::

    XFF_LOOSE_UNSAFE = True

If you want to keep the ``X-Forwarded-For`` header untouched even if
there are extra entries, use::

    XFF_CLEAN = False

Whitelisting
============

In some cases requests from alternate request paths are to be expected.
The Amazon Elastic Loadbalancer healthcheck or other administrative
tasks need to be available even if they do not match the criteria.

This library accepts URIs as regular expressions to be exempt for
checking. These will be exempt for any validation including
``XFF_STRICT`` and ``XFF_HEADER_REQUIRED``.

To define the whitelist::

    XFF_EXEMPT_URLS = [
        r'^healthcheck/$',
        r'^admin/',
    ]

This will allow calling ``/healthcheck/`` and ``/admin/*`` from anywhere.
It is a daft idea to allow everyone to access the admin site with less
requirements than the other parts of the site. For this reason it is
possible to respond with ``404`` (Not Found) when the request arrives
through the main entrance::

    XFF_EXEMPT_STEALTH = True

This will assume that anything below ``XFF_TRUSTED_PROXY_DEPTH`` is
trusted. The method is naive, but effective.

Logging
=======

Dropped requests will be logged. This means that there will be plenty of
logs when the library is misconfigured or malicious things are taking
place. It is recommended to keep the logs for tracing in case of a real
attack. However they can be filtered from development by setting::

    LOGGING = {
        'loggers': {
             'xff.middleware': {
                  'handlers': ['null'],
                  'propagate': False,
             },
         },
    }

Setting up
==========

It is recommended to enable the middleware with the assumed number of
proxies and investigating the logs. If the header is not present or the
middleware is not configured, there will be no log entries. If the logs
state that the depth is incorrect, it should be reduced. If all
requests are considered as spoofing, the depth should probably be
increased::

    MIDDLEWARE_CLASSES = [
        'xff.middleware.XForwardedForMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
    ]

    XFF_TRUSTED_PROXY_DEPTH = 2

When logs appear correct, control can be increased in increments::

    XFF_NO_SPOOFING = True

Then::

    XFF_STRICT = True

Defining exceptions is feasible with other flags set. The following
could be used behind an AWS Elastic Loadbalancer to prevent entry
without the proper header set but allow healthcheck to return
correctly. The stealth would also mask the same URI with a 404
error::

    XFF_TRUSTED_PROXY_DEPTH = 1
    XFF_EXEMPT_URLS = [r'^health/]
    XFF_REQUIRE_HEADER = True
    XFF_EXEMPT_STEALTH = True

In case there is a chain of reverse proxies, the healthcheck URI is
available for all layers except the last one.
