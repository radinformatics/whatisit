from celery.decorators import periodic_task
from celery import shared_task, Celery
from celery.schedules import crontab

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.utils import timezone

from notifications.signals import notify
from whatisit.settings import DOMAIN_NAME
from whatisit.apps.users.models import Team
from whatisit.apps.wordfish.models import (
    AllowedAnnotation,
    Annotation,
    ReportSet,
    Report
)

from whatisit.apps.wordfish.utils import (
    get_report_set
)

from whatisit.apps.users.utils import get_user

from datetime import datetime
from itertools import chain
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatisit.settings')
app = Celery('whatisit')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@shared_task
def generate_annotation_set(uid,user_ids,selection_keys,rid,N,testing_set,testing_set_correct,set_name,gid):
    '''generate annotation set is a task to select reports and generate an annotation set.
    If failed, will send a message to the user
    :param uid: the user id requesting, in case failed
    :param users: the (list, one or more) of user ids to include
    :param selection_keys: the list of selection keys
    :param rid: the report set id to generate for
    :param N: the number to include in the report set
    :param testing_set: the number to include in the testing set
    :param testing_set_correct: the total correct
    :param set_name: the name for the new report set
    :param gid: the unique id for the gold standard user
    '''
    report_set = get_report_set(rid)
    collection = report_set.collection

    # Try to get requester and gold standard annotator users
    try:
        requester = User.objects.get(uid)
        gold_standard = User.objects.get(gid)
    except:
        return False

    user = []
    for uid in user_ids:
        try:     
            add_user = User.objects.get(uid)
            user.append(add_user)
        except:
            pass

    if requester in collection.contributors.all() or requester == collection.owner:
        selections = []
        seen_annotations = []
        allowed_annotations = []
        for selection_key in selection_keys:
            name,label = selection_key.replace("whatisit||","").split("||")
            annotation_object = AllowedAnnotation.objects.get(name=name,
                                                              label=label)
            # We save the allowed annotation as a label to use for testing
            allowed_annotations.append(annotation_object)

            # Query to select the reports of interest
            selection = Annotation.objects.filter(annotator__in=user,
                                                  annotation=annotation_object,
                                                  reports__collection=collection)

            for annotation in selection:
                if annotation not in seen_annotations:
                    selections = list(chain(selections,annotation.reports.all()))
                    seen_annotations.append(annotation)

        # Remove reports that are already in sets
        existing = []
        existing_sets = ReportSet.objects.filter(collection=collection)
        for existing_set in existing_sets:
            existing = list(chain(existing,existing_set.reports.all()))
         selections = [report for report in selections if report not in existing]

        # If we have fewer selections left than options, no go
        if len(selections) < N:
            message = """You requested a new report set with %s reports for the %s collection. 
                         There are %s reports (not in a set) that match this criteria, and so we cannot
                         create new set.""" %(N,collection.name,len(selections))
            notify.send(requester, recipient=requester, verb=message)
            return False

        # Otherwise, save the new report set
        selections = selections[0:N]
        report_set = ReportSet.objects.create(collection=collection,
                                              number_tests=testing_set,
                                              number_reports=N,
                                              name=set_name,
                                              passing_tests=testing_set_correct,
                                              gold_standard=gold_standard)
        report_set.save()

        # Set creator should be allowed to see it
        report_set.annotators.add(requester)            
        report_set.reports = selections
        report_set.testing_annotations = allowed_annotations
        report_set.save()   

        # If we are successful, return a message to tell the admin to add annotators.
        add_annotators_link = "/collections/%s/sets/annotators" %(report_set.id)
        message = """Report set %s (N=%s reports) for the %s collection 
                     has been successfully created.""" %(set_name,N,collection.name)
        notify.send(requester, recipient=requester, verb=message)


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
