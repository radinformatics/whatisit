from celery.decorators import periodic_task
from celery import shared_task, Celery
from celery.schedules import crontab

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.utils import timezone

from whatisit.settings import DOMAIN_NAME
from whatisit.apps.users.models import Team
from whatisit.apps.wordfish.models import (
    AllowedAnnotation,
    Annotation,
    Report
)

from datetime import datetime
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatisit.settings')
app = Celery('whatisit')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@shared_task
def update_user_annotation(user,allowed_annotation,report):
    '''update_user_annotation will take a user, and an annotation, a report (object or id), and update the report with the annotation.
    :param user: the user object or user id
    :param allowed_annotation: the allowed annotation object or id
    :param report: the report object or id
    '''
    if not isinstance(user,User):
        user = User.objects.get(id=user)

    if not isinstance(allowed_annotation,AllowedAnnotation):
        allowed_annotation = AllowedAnnotation.objects.get(id=allowed_annotation)

    if not isinstance(report,Report):
        report = Report.objects.get(id=report)

    # Remove annotations done previously by the user for the report
    previous_annotations = Annotation.objects.filter(annotator=user,
                                                     reports__id=report.id,
                                                     annotation__name=allowed_annotation.name)
    annotation,created = Annotation.objects.get_or_create(annotator=user,
                                                          annotation=allowed_annotation)

    # If the annotation was just created, save it, and add report
    if created == True:
        annotation.save()
    annotation.reports.add(report)
    annotation.save()
    
    # Finally, remove the report from other annotation objects 
    for pa in previous_annotations:
        if pa.id != annotation.id:
            pa.reports.remove(report) 
            pa.save() # not needed       

    return annotation.id
