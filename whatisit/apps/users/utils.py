from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from whatisit.apps.wordfish.models import (
    ReportCollection,
    ReportSet
)
from whatisit.apps.users.models import (
    Credential,
    RequestPermission
)
import collections
import operator
import os


def get_has_credentials(report_set,return_users=True):
    '''get a list of users that have credentials (either status is TESTING or PASSED) for
    a report set.
    :param return_users: return list of users (not credentials) default is True
    '''
    has_credential = Credential.objects.filter(report_set=report_set,
                                               status__in=["TESTING","PASSED"])
    if return_users == True:
        has_credential = [x.user for x in has_credential]
    return has_credential


def get_credentials(users,report_set):
    '''get a list of credential objects for a group of users for a report_set
    '''
    credentials = Credential.objects.filter(report_set=report_set,
                                            user__in=users)
    return credentials


def get_credential_contenders(report_set,return_users=True):
    '''get a list of users that have permission to annotate a collection, but have
    not had a credential created.
    :param return_users: return list of users (not credentials) default is True
    '''
    # Get list of allowed annotators for set, not in set (to add)
    all_annotators = RequestMembership.objects.filter(collection=report_set.collection)
    all_annotators = [x.requester for x in all_annotators]
    has_credential = get_has_credential(report_set)
    contenders = [user for user in all_annotators if user not in has_credentials]
    return contenders


def get_annotation_status(report_set,user):
    '''get_annotation_status ensures that a user is approved to annotate, and has been 
    recently tested (within the time specified by the report set) to continue annotating.
    If the user is approved and not needs testing, status is APPROVED
    If the user is testing, status is TESTING
    If the user is approved and needs testing, status is changed to TESTING.
    If the user is denied, status is DENIED.
    :param report_set: the report_set to check
    :param user: the user to check status for
    '''
    try:
        Credential.objects.get(report_set=report_set,
                               user=user)
    except Credential.DoesNotExist:
        return None


    user = models.ForeignKey(User,related_name="user_credential_for")
    report_set = models.ForeignKey(ReportSet,related_name="report_set_credential_for")
    created_at = models.DateTimeField('date of credential creation', auto_now_add=True)
    updated_at = models.DateTimeField('date of updated credential', auto_now=True)
    status = models.CharField(max_length=200, null=False, verbose_name="Status of credential", default="TESTING",choices=STATUS_CHOICES)
    duration_weeks = models.CharField(max_length=100,null=False,default="2",verbose_name="Duration of credential, in weeks")

