from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Don't run tasks; each test patches apply_async where needed
CELERY_TASK_ALWAYS_EAGER = False

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

ANTHROPIC_API_KEY = 'test-key-not-real'
