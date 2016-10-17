from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatisit.settings')
witcelery = Celery('whatisit')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
witcelery.config_from_object('django.conf:settings')
witcelery.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
