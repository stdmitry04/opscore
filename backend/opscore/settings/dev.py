from .base import *

DEBUG = True

DATABASES['default']['NAME'] = os.getenv('DB_NAME', 'opscore')
