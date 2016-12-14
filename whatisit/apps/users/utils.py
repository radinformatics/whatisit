from django.contrib.auth.models import User
from django.http.response import (
    HttpResponseRedirect, 
    HttpResponseForbidden, 
    Http404
)
from django.shortcuts import (
    get_object_or_404, 
    render_to_response, 
    render, 
    redirect
)
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
from itertools import chain
from numpy import unique
import operator
import os

from whatisit.apps.users.models import Credential, Team

def get_user(request,uid):
    '''get a single user, or return 404'''
    keyargs = {'id':uid}
    try:
        user = User.objects.get(**keyargs)
    except User.DoesNotExist:
        raise Http404
    else:
        return user

def get_team(request,tid):
    '''get a single team, or return 404'''
    keyargs = {'id':tid}
    try:
        team = Team.objects.get(**keyargs)
    except Team.DoesNotExist:
        raise Http404
    else:
        return team


def get_credential(request,cid):
    '''get a credential, or return 404'''
    keyargs = {'id':cid}
    try:
        cred = Credential.objects.get(**keyargs)
    except Credential.DoesNotExist:
        raise Http404
    else:
        return cred



def has_credentials(report_set,return_users=True,status=None):
    '''get a list of users that have credentials (either status is TESTING or PASSED) for
    a report set.
    :param return_users: return list of users (not credentials) default is True
    :param status: one or more status to get. If not defined, will use TESTING and PASSED
    '''
    if status == None:
        status = ["TESTING","APPROVED"]
    if not isinstance(status,list):
        status = [status]
    has_credential = Credential.objects.filter(report_set=report_set,
                                               status__in=status)
    if return_users == True:
        has_credential = [x.user for x in has_credential]
    return has_credential


def get_user_report_sets(collection,user,status=None):
    '''get a list of report sets for which a user has one or more status (default)
    TESTING for a collection
    '''
    if status == None:
        status = "TESTING"
    if not isinstance(status,list):
        status = [status]
    report_set_contenders = ReportSet.objects.filter(collection=collection)
    report_sets = []

    for report_set_contender in report_set_contenders:
        has_credential = Credential.objects.filter(report_set=report_set_contender,
                                                   status__in=status,
                                                   user=user).exists()
        if has_credential:
            report_sets.append(report_set_contender)
    return report_sets        


def get_credentials(users,report_set):
    '''get a list of credential objects for a group of users for a report_set
    '''
    credentials = Credential.objects.filter(report_set=report_set,
                                            user__in=users)
    return credentials


def get_credential_contenders(report_set,return_users=True,status=None):
    '''get a list of users that are APPROVED (or other status) to 
    annotate a collection, but have not had a credential created.
    :param return_users: return list of users (not credentials) default is True
    :param status: the status to filter for. If not provided, deafult is APPROVED
    '''
    if status==None:
        status = "APPROVED"
    # Get list of allowed annotators for set, not in set (to add)
    all_annotators = RequestMembership.objects.filter(collection=report_set.collection,status=status)
    annotator_ids = unique([x.requester.id for x in all_annotators] + [a.id for a in report_set.collection.annotators.all()]).tolist()
    all_annotators = User.objects.filter(id__in=annotator_ids)
    contenders = [user for user in all_annotators if user not in has_credentials(report_set)]
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


####################################################################################
# TEAM FUNCTIONS ###################################################################
####################################################################################


def get_user_team(request):
    ''' get the team of the authenticated user
    '''
    if request.user.is_authenticated():
        user_team = Team.objects.filter(members=request.user)
        if len(user_team) > 0:
            return user_team[0]
    return None


def remove_user_teams(remove_teams,user):
    '''removes a user from one or more teams
    :param remove_teams: the list of teams to remove the user from
    :param user: the user to remove
    :returns: previous team removed from (user only allowed one at a time)
    '''
    previous_team = None
    if not isinstance(remove_teams,list):
        remove_teams = [remove_teams]
    for remove_team in remove_teams:
        if user in remove_team.members:
            previous_team = remove_team
            remove_team.members = [x for x in remove_team.members if x != user]
            remove_team.save()
    return previous_team


def has_team_edit_permission(request,team):
    '''only the owner of a team can edit it.
    '''
    if request.user in team.members.all():
        return True
    return False
