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

def get_report(request,cid):
    '''get a single report, or return 404'''
    keyargs = {'id':cid}
    try:
        report = Report.objects.get(**keyargs)
    except Report.DoesNotExist:
        raise Http404
    else:
        return report


def get_report_collection(request,cid):
    '''get a single collection, or return 404'''
    keyargs = {'id':cid}
    try:
        collection = ReportCollection.objects.get(**keyargs)
    except ReportCollection.DoesNotExist:
        raise Http404
    else:
        return collection


def get_report_set(request,sid):
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
    '''
    # Return count for a single user
    if isinstance(users,User):
        return Annotation.objects.filter(annotator=users).count()
    # or count across a group of users
    return Annotation.objects.filter(annotator__in=users).count() 
   

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


def update_user_annotation(user,annotation_object,report):
    '''update_user_annotation will take a user, and an annotation object, a report, and update the report with the annotation.
    :param user: the user object
    :param annotation_object: the annotation
    '''

    # Remove annotations done previously by the user for the report
    previous_annotations = Annotation.objects.filter(annotator=user,
                                                     reports__id=report.id,
                                                     annotation__name=annotation_object.name)
    annotation,created = Annotation.objects.get_or_create(annotator=user,
                                                          annotation=annotation_object)

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

    return annotation


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
    allowed = AllowedAnnotation.objects.filter(annotation__reports__collection=collection)
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


#TODO: edit these to upload reports 
def save_image_upload(collection,image,report=None):
    '''save_image_upload will save an image object to a collection
    :param collection: the collection object
    :param report: the report object, e.g., if updating
    '''
    if report==None:
        report = report(collection=collection)
    collection_dir = "%s/%s" %(MEDIA_ROOT,collection.id)
    if not os.path.exists(collection_dir):
        os.mkdir(collection_dir)
    report_file = '%s/%s' %(collection_dir,image.name)
    with open(report_file, 'wb+') as destination:
        for chunk in image.chunks():
            destination.write(chunk)
    report.name = image.name
    report.version = get_image_hash(report_file)
    report.image = image
    report.image.name = image.name
    report.save()
    return report


def save_package_upload(collection,image,report=None):
    '''save_package_upload will save an image object extracted from a package to a collection
    this is currently not in use, as most users will not package reports.
    :param collection: the collection object
    :param report: the report object, e.g., if updating
    '''
    if report==None:
        report = report(collection=collection)
    collection_dir = "%s/%s" %(MEDIA_ROOT,collection.id)
    if not os.path.exists(collection_dir):
        os.mkdir(collection_dir)
    report_file = '%s/%s' %(collection_dir,image.name)
    with open(report_file, 'wb+') as destination:
        for chunk in image.chunks():
            destination.write(chunk)
    report.name = image.name
    report.version = get_image_hash(report_file)
    report.image = image
    report.image.name = image.name
    report.save()
    return report


def save_package(collection,package,report=None):
    '''save_package_upload will save a package object to a collection
    by way of extracting the image to a temporary location, and
    adding meta data to the report
    :param collection: the collection object
    :param package: the full path to the package
    :param report: the report object, e.g., if updating
    '''
    if report==None:
        report = report(collection=collection)
    collection_dir = "%s/%s" %(MEDIA_ROOT,collection.id)
    if not os.path.exists(collection_dir):
        os.mkdir(collection_dir)
    # Unzip the package image to a temporary directory
    includes = list_package(package)
    image_path = [x for x in includes if re.search(".img$",x)]
    # Only continue if an image is found in the package
    if len(image_path) > 0:
        image_path = image_path[0]
        # The new file will be saved to the collection directory
        new_file = '%s/%s' %(collection_dir,image_path)
        contents = load_package(package)
        tmp_file = contents[image_path]
        report.name = image_path
        report.version = get_image_hash(tmp_file)
        image = File(open(tmp_file,'rb'),image_path)
        with open(new_file, 'wb+') as destination:
            for chunk in image.chunks():
                destination.write(chunk)
        report.image = new_file
        report.save()
        # Add the report to the collection
        collection.report_set.add(report)
        collection.save
        # Clean up temporary directory
        shutil.rmtree(os.path.dirname(tmp_file))
        return report
    return None


def add_message(message,context):
    '''add_message will add a message to the context
    :param message: the message (list or string) to add
    :param context: the context (dict) for the template view
    '''
    # Messages must be in a list
    if message != None:
        if not isinstance(message,list):
            message = [message]
        context["messages"] = message
    return context


def format_report_name(name,special_characters=None):
    '''format_report_name will take a name supplied by the user,
    remove all special characters (except for those defined by "special-characters"
    and return the new image name.
    '''
    if special_characters == None:
        special_characters = []
    return ''.join(e.lower() for e in name if e.isalnum() or e in special_characters)
