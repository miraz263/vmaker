import os
from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'story_animator.settings')


app = Celery('story_animator')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()