from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from whatisit.apps.wordfish.models import (
    ReportCollection,
    ReportSet
)
from whatisit.apps.users.models import (
    Credential,
    RequestMembership
)
import collections
from datetime import datetime
from datetime import timedelta
import operator
import os

from whatisit.apps.users.models import Credential

def get_user(request,uid):
    '''get a single user, or return 404'''
    keyargs = {'id':uid}
    try:
        user = User.objects.get(**keyargs)
    except User.DoesNotExist:
        raise Http404
    else:
        return user


def get_credential(request,cid):
    '''get a credential, or return 404'''
    keyargs = {'id':cid}
    try:
        cred = Credential.objects.get(**keyargs)
    except Credential.DoesNotExist:
        raise Http404
    else:
        return cred


def has_credentials(report_set,return_users=True):
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


def needs_testing(credential):
    '''compare the time from the users last time to the time now. If it's greater than the
    time allowed for the credential, the user must test again.
    '''
    if credential.updated_at == None:
        return True

    # How many weeks between testings?
    maximum_time = int(credential.duration_weeks)
    days = maximum_time * 7

    # If the credential was updated less than 2 weeks ago, no testing
    if credential.updated_at + timedelta(days=days) < datetime.now():
        return False

    # Otherwise, we need testing
    return True


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
        credential = Credential.objects.get(report_set=report_set,
                                            user=user)
    except Credential.DoesNotExist:
        return None

    if credential.status == "APPROVED":
        if needs_testing(credential):
            credential.status = "TESTING"
            credential.save()

    return credential.status
