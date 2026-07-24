import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'opscore.settings.dev')

app = Celery('opscore')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'nightly-report': {
        'task': 'apps.tasks.tasks.generate_report',
        'schedule': crontab(hour=2, minute=0),
        'args': (['all'],),
    },
    'reindex-embeddings': {
        'task': 'apps.tasks.tasks.reindex_stale_documents',
        'schedule': crontab(hour=3, minute=0),
    },
}
