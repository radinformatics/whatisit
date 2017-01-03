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
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
from django.core.files.base import ContentFile
from django.core.files import File
from django.db.models.aggregates import Count
from itertools import chain
from whatisit.apps.users.models import Team
from whatisit.apps.wordfish.models import (
    AllowedAnnotation, 
    Annotation,
    Report,
    ReportCollection,
    ReportSet
)
from whatisit.settings import MEDIA_ROOT
from random import randint
from numpy.random import shuffle
import numpy
import operator
import shutil
import os
import re


#### GETS #############################################################

def get_report(rid):
    '''get a single report, or return 404'''
    keyargs = {'id':rid}
    try:
        report = Report.objects.get(**keyargs)
    except Report.DoesNotExist:
        raise Http404
    else:
        return report


def get_report_collection(cid):
    '''get a single collection, or return 404'''
    keyargs = {'id':cid}
    try:
        collection = ReportCollection.objects.get(**keyargs)
    except ReportCollection.DoesNotExist:
        raise Http404
    else:
        return collection


def get_report_set(sid):
    '''get a report set, or return 404'''
    keyargs = {'id':sid}
    try:
        report_set = ReportSet.objects.get(**keyargs)
    except ReportSet.DoesNotExist:
        raise Http404
    else:
        return report_set


def get_collection_users(collection):
    '''get_collection_users will return a list of all owners and contributors for
    a collection
    :param collection: the collection object to use
    '''
    contributors = collection.contributors.all()
    owner = collection.owner
    return list(chain(contributors,[owner]))


def get_collection_annotators(collection):
    '''get_collection_annotators will return a list of those who have annotated
    the collection
    :param collection: the collection object to use
    '''
    annotators = Annotation.objects.filter(reports__collection=collection).values('annotator').distinct()
    unique_annotators = [x['annotator'] for x in list(annotators)] 
    unique_annotators = numpy.unique(unique_annotators).tolist()
    annotators = User.objects.filter(id__in=unique_annotators)
    return annotators


def get_annotation_counts(collection,reports=None):
    '''get_annotation_counts will return a dictionary with annotation labels, values,
    and counts for all allowed_annotations for a given collection
    :param collection: the collection to get annotation counts for
    :param reports: if defined, return counts for only that set. Otherwise, count all.
    '''
    # What annotations are allowed across the report collection?
    annotations_allowed = get_allowed_annotations(collection)

    # Take a count
    counts = dict()
    total = 0
    for annotation_allowed in annotations_allowed:
        if annotation_allowed.name not in counts:
            counts[annotation_allowed.name] = {}
        if reports == None:
            report_n = annotation_allowed.annotation_set.values_list('reports', flat=True).distinct().count()
        else: 
            report_n = annotation_allowed.annotation_set.filter(reports__in=reports).count()
        counts[annotation_allowed.name][annotation_allowed.label] = report_n
        total += report_n
    counts['total'] = total

    return counts    


#### Teams #############################################################

def count_user_annotations(users):
    '''return the count of a single user's annotations 
    (meaning across reports)
    '''

    # Count for a single user
    if isinstance(users,User):
        count = Report.objects.filter(reports_annotated__annotator=users).distinct().count()

    # or count across a group of users
    else:
        count = Report.objects.filter(reports_annotated__annotator__in=users).distinct().count()

    return count
   

def count_remaining_reports(user,collection,return_message=False,sid=None):
    '''count remaining reports is a wrapper function to count reports
    in a collection or set, and return either the count or a message to indicate
    the number remaining.
    :param user: the user to count for
    :param collection: the collection to count for
    :param return_message: if True, return a message (str) instead of count
    :param sid: a report set id. If provided, will return counts relevant to a set
    '''

    if sid != None:
        report_set = get_report_set(sid)
        remaining = count_user_reports(user,report_set)
        message = "You have annotated %s of %s reports in this set." %(remaining,report_set.number_reports)
    else:
        remaining = count_user_annotations(user)
        message = "You have annotated %s reports." %(remaining)

    if return_message == True:
        return message
    return remaining


def count_user_reports(user,report_set):
    '''return the count of a single user's reports annotated
    :param report_set: a report set to count for
    '''
    return report_set.reports.filter(reports_annotated__annotator=user).distinct().count()



def summarize_team_annotations(members):
    '''summarize_team_annotations will return a summary of annotations for a group of users, typically a team
    :param members: a list or queryset of users
    '''
    counts = dict()
    total = 0
    for member in members:
        member_count = count_user_annotations(member)
        counts[member.username] = member_count
        total += member_count
    counts['total'] = total
    return counts    


def summarize_teams_annotations(teams,sort=True):
    '''summarize_teams_annotations returns a sorted list with [(team:count)] 
    :param members: a list or queryset of users
    :param sort: sort the result (default is True)
    '''
    sorted_teams = dict()
    for team in teams:
        team_count = summarize_team_annotations(team.members.all())['total']
        sorted_teams[team.id] = team_count
    if sort == True:
        sorted_teams = sorted(sorted_teams.items(), key=operator.itemgetter(1))
        sorted_teams.reverse() # ensure returns from most to least
    return sorted_teams


def get_annotations(user=None,report=None):
    '''get_user_annotations will return the Annotation objects for a user and report
    :param user: the user to return objects for
    :param report: the report object to return for
    '''
    if user != None and report != None:
        return Annotation.objects.filter(reports__report_id=report.report_id,annotator=user).annotate(Count('annotation', distinct=True))
    elif user == None and report == None:
        return []
    elif user == None:
        return Annotation.objects.filter(reports__report_id=report.report_id).annotate(Count('annotation', distinct=True))
    else: # report is None
        return Annotation.objects.filter(annotator=user).annotate(Count('annotation', distinct=True))


def clear_user_annotations(user,report):
    '''clear_user_annotations will remove all annotations for a user for a report.
    :param user: the user
    :param report: the report object to clear
    '''
    previous_annotations = Annotation.objects.filter(annotator=user,
                                                     reports__id=report.id)
    for previous_annotation in previous_annotations:
        if report in previous_annotation.reports.all(): # in case multiple processes
            previous_annotation.reports.remove(report) 


def group_allowed_annotations(allowed_annotations):
    '''group_allowed_annotations will take a list of allowed annotations for a collection (or other)
    and put them together in a dictionary by the annotation name
    :param allowed_annotations: a list (queryset) of allowed annotations
    '''
    annotation_set = dict()
    for allowed_annotation in allowed_annotations:
        # Is the key (the annotation primary name) in our lookup?
        if allowed_annotation.name not in annotation_set:
            annotation_set[allowed_annotation.name] = []
        # Is the value (the annotation option) in our list?
        if allowed_annotation.label not in annotation_set[allowed_annotation.name]:
            annotation_set[allowed_annotation.name].append(allowed_annotation.label)
    return annotation_set


def summarize_annotations(annotations):
    '''summarize_annotations will return a list of annotations for a report, with key value
    corresponding to name:label, and also include the count for each
    :param annotations: a list (queryset) of annotations
    '''
    summary = dict()
    counts = dict()
    for annotation in annotations:
        summary[annotation.annotation.name] = annotation.annotation.label
        counts[annotation.annotation.name] = annotation.annotation__count
    result = {"labels":summary,
              "counts":counts}
    return result


def get_allowed_annotations(collection,return_objects=True):
    '''get_allowed_annotations will return allowed annotations for a collection
    :param collection: the collection to select
    :param return_objects: if False, returns dictionary of objects
    '''
    allowed = collection.allowed_annotations.all().distinct()
    if return_objects == False:
        allowed = group_allowed_annotations(allowed)
    return allowed


###########################################################################################
## SELECTION ALGORITHMS
###########################################################################################

def select_random_reports(reports,N=1):
    '''select random reports will select N reports from a provided set.
    '''
    reports = list(reports)
    shuffle(reports)
    # If enough reports are provided, select subset
    if len(reports) >= N:
        reports = reports[0:N]
    return reports


def select_random_report(reports):
    '''select random report will return one random report
    :NOTE this function was buggy when used with report_set,
    select_random_reports is being used in favor (needs testing)
    '''
    rid = None
    while rid == None:
        count = reports.aggregate(count=Count('id'))['count']
        rid = randint(0, count - 1)
        try:
            record = Report.objects.get(id=rid)
        except:
            rid = None
    return record


def format_report_name(name,special_characters=None):
    '''format_report_name will take a name supplied by the user,
    remove all special characters (except for those defined by "special-characters"
    and return the new image name.
    '''
    if special_characters == None:
        special_characters = []
    return ''.join(e.lower() for e in name if e.isalnum() or e in special_characters)
