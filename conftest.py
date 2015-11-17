from django.conf import settings


def pytest_configure():
    import sys

    try:
        import django  # NOQA
    except ImportError:
        print("Error: django not installed")
        sys.exit(1)

    settings.configure(
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.admin',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'tests.app',
            'xff',
        ],
        MIDDLEWARE_CLASSES=(
            'xff.middleware.XForwardedForMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ),
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        ROOT_URLCONF='tests.app.urls',
        DEBUG=True,
        TEMPLATE_DEBUG=True,
        LOGGING={},
        XFF_EXEMPT_URLS=[r'^/health/$']
    )
