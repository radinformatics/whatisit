from whatisit.apps.wordfish.forms import (
    ReportForm, 
    ReportCollectionForm,
)

from whatisit.apps.wordfish.models import (
    Annotation, 
    AllowedAnnotation,
    Report, 
    ReportCollection,
    ReportSet
)

from whatisit.apps.wordfish.tests import (
    test_annotator
)

from whatisit.apps.main.utils import (
    parse_numeric_input
)

from whatisit.apps.wordfish.utils import (
    clear_user_annotations,
    count_remaining_reports,
    count_user_annotations,
    get_allowed_annotations,
    get_annotation_counts, 
    get_annotations, 
    get_collection_users,
    get_collection_annotators,
    get_report,
    get_report_collection,
    get_report_set,
    group_allowed_annotations,
    select_random_report,
    select_random_reports,
    summarize_annotations
)

from whatisit.apps.wordfish.tasks import (
    update_user_annotation,
    generate_annotation_set
)

from whatisit.settings import (
    BASE_DIR, 
    MEDIA_ROOT,
    GOLD_STANDARD_MIN_ANNOTS
)

from whatisit.apps.users.models import RequestMembership, Credential
from whatisit.apps.users.utils import (
    get_annotation_status,
    has_credentials, 
    get_credential_contenders, 
    get_credentials,
    get_user,
    get_user_report_sets
)
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models.aggregates import Count
from django.forms.models import model_to_dict
from django.http import HttpResponse, JsonResponse
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

from django.utils import timezone
from django.urls import reverse

import csv
import datetime
import gzip
import hashlib
from itertools import chain
import json
import os
import numpy
import pandas
import pickle
import re
import shutil
import tarfile
import tempfile
import traceback
import uuid
import zipfile

media_dir = os.path.join(BASE_DIR,MEDIA_ROOT)


###############################################################################################
# Authentication and Collection View Permissions###############################################
###############################################################################################


@login_required
def get_permissions(request,context):
    '''get_permissions returns an updated context with edit_permission and annotate_permission
    for a user. The key "collection" must be in the context
    '''
    collection = context["collection"]

    # Edit and annotate permissions?
    context["edit_permission"] = has_collection_edit_permission(request,collection)
    context["annotate_permission"] = has_collection_annotate_permission(request,collection)
    context["delete_permission"] = request.user == collection.owner
    
    # If no annotate permission, get their request
    if context["annotate_permission"] == False:
        try:
            context['membership'] = RequestMembership.objects.get(requester=request.user,
                                                                  collection=collection)
        except:
            pass
    return context


# Does a user have permissions to see a collection?

def has_delete_permission(request,collection):
    '''collection owners have delete permission'''
    if request.user == collection.owner:
        return True
    return False


def has_collection_edit_permission(request,collection):
    '''owners and contributors have edit permission'''
    if request.user == collection.owner or request.user in collection.contributors.all():
        return True
    return False


def has_collection_annotate_permission(request,collection):
    '''owner and annotators have annotate permission (not contributors)'''
    if request.user == collection.owner:
        return True
    elif request.user in collection.annotators.all():
        return True
    return False


@login_required
def request_annotate_permission(request,cid):    
    '''request_annotate_permission will allow a user to request addition to
    a collection (as an annotator) via a RequestMembership object. This does not
    give full access to annotate, they must then be added to specific annotation sets
    '''
    collection = get_report_collection(cid)
    previous_request,created = RequestMembership.objects.get_or_create(requester=request.user,
                                                                       collection=collection)
    if created == True:
        previous_request.save()

    # redirect back to collection with message
    messages.success(request, 'Request sent.')
    return view_report_collection(request,cid)


@login_required
def deny_annotate_permission(request,cid,uid):
    '''a user can be denied annotate permission at the onset (being asked) or
    have it taken away, given asking --> pending --> does not pass test
    '''
    collection = get_report_collection(cid)
    if has_collection_edit_permission(request,collection):
        requester = get_user(request,uid)
        permission_request = RequestMembership.objects.get(collection=collection,
                                                           requester=requester)
        if permission_request.status not in ["APPROVED","DENIED"]:
            permission_request.status = "DENIED"
            permission_request.save()
            messages.success(request, 'Annotators updated.')    
    return view_report_collection(request,cid)


@login_required
def approve_annotate_permission(request,cid,uid):
    '''a user must first get approved for annotate permission before being
    added to an annotation set
    '''
    collection = get_report_collection(cid)
    if has_collection_edit_permission(request,collection):
        requester = get_user(request,uid)
        permission_request = RequestMembership.objects.get(collection=collection,
                                                           requester=requester)
        if permission_request.status not in ["APPROVED","DENIED"]:

            # Update the collection
            collection.annotators.add(requester)
            collection.save()

            # Update the permission request
            permission_request.status = "APPROVED"
            permission_request.save()

            messages.success(request, 'Annotators approved.')
    
    return view_report_collection(request,cid)

###############################################################################################
# Contributors ################################################################################
###############################################################################################

@login_required
def edit_contributors(request,cid):
    '''edit_contributors is the view to see, add, and delete contributors for a set.
    '''
    collection = get_report_collection(cid)
    if request.user == collection.owner:

        # Who are current contributors?
        contributors = collection.contributors.all()

        # Any user that isn't the owner or already a contributor can be added
        invalid_users = [x.id for x in contributors] + [request.user.id]
        contenders = [x for x in User.objects.all() if x.username != 'AnonymousUser']
        contenders = [x for x in contenders if x.id not in invalid_users]

        context = {'contributors':contributors,
                   'collection':collection,
                   'contenders':contenders}
        
        return render(request, 'reports/edit_collection_contributors.html', context)

    # Does not have permission, return to collection
    messages.info(request, "You do not have permission to perform this action.")
    return view_report_collection(request,cid)


@login_required
def add_contributor(request,cid):
    '''add a new contributor to a collection
    :param cid: the collection id
    '''
    collection = get_report_collection(cid)
    if request.user == collection.owner:
        if request.method == "POST":
            user_id = request.POST.get('user',None)
            if user_id:
                user = get_user(request,user_id)
                collection.contributors.add(user)
                collection.save()
                messages.success(request, 'User %s added as contributor to collection.' %(user))

    return edit_contributors(request,cid)


@login_required
def remove_contributor(request,cid,uid):
    '''remove a contributor from a collection
    :param cid: the collection id
    :param uid: the contributor (user) id
    '''
    collection = get_report_collection(cid)
    user = get_user(request,uid)
    contributors = collection.contributors.all()
    if request.user == collection.owner:
        if user in contributors:    
            collection.contributors = [x for x in contributors if x != user]
            collection.save()
            messages.success(request, 'User %s is no longer a contributor to the collection.' %(contributor))

    return edit_contributors(request,cid)


###############################################################################################
# Set Annotation Permission ###################################################################
###############################################################################################

@login_required
def edit_set_annotators(request,sid):
    '''edit_set_annotators allows a collection owner to add/remove users to an annotation set
    this means that the user has asked for and been given permission to annotate the collection.
    :param sid: the report set id
    '''
    report_set = get_report_set(sid)
    collection = report_set.collection
    if has_collection_edit_permission(request,collection):

        # Get list of allowed annotators for set, not in set (to add)
        has_credential = has_credentials(report_set,status="PASSED")
        denied_credential = has_credentials(report_set,status="DENIED")

        # Get credentials for allowed annotators
        credentials = get_credentials(has_credential,report_set)
        users_with_credentials = [x.user for x in credentials]

        # Get list of allowed annotators for set, allowed in set (if want to remove)
        contenders = get_credential_contenders(report_set)

        # Get list of failed annotators for set (if want to retest)
        failures = get_credentials(denied_credential,
                                   report_set,
                                   status="DENIED")

        # Remove contenders that are allowed annotation
        contenders = [x for x in contenders if x not in users_with_credentials]

        context = {'annotators':credentials,
                   'collection':collection,
                   'contenders':contenders,
                   'report_set':report_set,
                   'failures':failures}
        
        return render(request, 'reports/report_collection_annotators.html', context)

    # Does not have permission, return to collection
    messages.info(request, "You do not have permission to edit annotators for this collection.")
    return view_report_collection(request,cid)



@login_required
def change_set_annotator(request,sid,uid,status):
    '''change the status of a set annotator to one of 
    PASSED,DENIED,TESTING
    :param sid: the report_set id
    :param uid: the user id
    '''
    report_set = get_report_set(sid)
    collection = report_set.collection
    if has_collection_edit_permission(request,collection):
        annotator = get_user(request,uid)
        credential = Credential.objects.get(user=annotator,
                                            report_set=report_set)
        credential.status = status
        credential.save()
        messages.info(request,"User %s status changed to %s" %(annotator,status.lower()))
        return edit_set_annotators(request,sid)

    # Does not have permission, return to collection
    messages.info(request, "You do not have permission to edit annotators for this collection.")
    return view_report_collection(request,cid)



@login_required
def new_set_annotator(request,sid):
    '''creates a new Credential for a user and a particular 
    collection, with default state TESTING to ensure tests first.
    :param sid: the report_set id
    '''
    report_set = get_report_set(sid)
    collection = report_set.collection
    if has_collection_edit_permission(request,collection):
        if request.method == "POST":
            user_id = request.POST.get('user',None)
            if user_id:
                user = get_user(request,user_id)
                credential = Credential.objects.create(user=user,
                                                       report_set=report_set)
                credential.save()
                messages.success(request, 'Credential for user %s added, user will need to test before annotating.' %(user))

    return edit_set_annotators(request,sid)




@login_required
def approve_set_annotator(request,sid,uid):
    '''give the user APPROVED status for a report_set
    :param sid: the report_set id
    :param uid: the user id
    '''
    return change_set_annotator(request,sid,uid,"PASSED")


@login_required
def deny_set_annotator(request,sid,uid):
    '''deny the user (DENIED status) permission to annotate a report_set
    :param sid: the report_set id
    :param uid: the user id
    '''
    return change_set_annotator(request,sid,uid,"DENIED")


@login_required
def test_set_annotator(request,sid,uid):
    '''force the user to retest (TESTING status) to annotate a report_set
    :param sid: the report_set id
    :param uid: the user id
    '''
    return change_set_annotator(request,sid,uid,"TESTING")


@login_required
def remove_set_annotator(request,sid,uid):
    '''completely remove a user from an annotation set.
    :param sid: the report_set id
    :param uid: the user id
    '''
    report_set = get_report_set(sid)
    collection = report_set.collection
    if has_collection_edit_permission(request,collection):
        annotator = get_user(request,uid)
        credential = Credential.objects.get(user=annotator,
                                            report_set=report_set)
        credential.delete()
        messages.info(request, "User %s has been removed from set annotators." %(annotator))
        return render(request, 'reports/report_collection_annotators.html', context)

    # Does not have permission, return to collection
    messages.info(request, "You do not have permission to edit annotators for this collection.")
    return view_report_collection(request,cid)



###############################################################################################
# reportS ##################################################################################
###############################################################################################

# View all collections
def view_report_collections(request):
    has_collections = False
    collections = ReportCollection.objects.filter(private=False)
    context = {"collections":collections,
               "page_title":"Report Collections"}
    return render(request, 'reports/all_reports.html', context)


# Personal collections
@login_required
def my_report_collections(request):
    collections = ReportCollection.objects.filter(owner=request.user)
    context = {"collections":collections,
               "page_title":"My Collections"}
    return render(request, 'reports/all_reports.html', context)


# View report collection
@login_required
def view_report_collection(request,cid):
    collection = get_report_collection(cid)
    report_count = collection.report_set.count()
    annotation_count = count_user_annotations(collection.annotators.all())
    context = {"collection":collection,
               "report_count":report_count,
               "annotation_count":annotation_count}

    # Get all permissions, context must have collection as key
    context = get_permissions(request,context)

    # If the user has edit_permissions, we want to show him/her users that can be added
    if context["edit_permission"] == True:
        context["requesters"] = RequestMembership.objects.filter(collection=collection)
        context["requesters_pending"] = len([x for x in context["requesters"] if x.status == "PENDING"])

    # Show report Sets allowed to annotate
    context["report_sets"] = ReportSet.objects.filter(annotators__in=[request.user],
                                                      collection=collection)
    context['report_set_testers'] = get_user_report_sets(collection,
                                                         user=request.user) # status="TESTING"

    return render(request, 'reports/report_collection_details.html', context)


@login_required
def save_collection_markup(request,cid):
    collection = get_report_collection(cid)
    edit_permission = has_collection_edit_permission(request,collection)
    if request.method == "POST":
        if edit_permission:
            markup = request.POST.get('markup',None)
            if markup:
                collection.markup = markup
                collection.save()
                messages.success(request, 'Collection markup saved.')

    return view_report_collection(request,cid)


# View report collection
@login_required
def summarize_reports(request,cid):
    collection = get_report_collection(cid)
    # Get a count of annotations by label in the collection
    annotation_counts = get_annotation_counts(collection)
    report_count = Report.objects.filter(collection=collection).count()
    context = {"collection":collection,
               "annotation_counts":annotation_counts,
               "report_count":report_count}
    return render(request, 'reports/report_collection_summary.html', context)


# View report
@login_required
def view_report(request,rid):
    report = get_report(rid)
    #TODO: In the future if we ever want to allow counting across collection, this needs to change
    annotation_counts = get_annotation_counts(report.collection,reports=[report])
    context = {"report":report,
               "annotation_counts":annotation_counts,
               "collection":report.collection}

    # Get all permissions, context must have collection as key
    context = get_permissions(request,context)

    return render(request, 'reports/report_details.html', context)


# Delete report
@login_required
def delete_report(request,rid):
    report = get_report(rid)
    collection = report.collection
    if request.user == collection.owner:
        report.delete()
    else:
        messages.warning(request, "You are not authorized to perform this operation.")
    return HttpResponseRedirect(collection.get_absolute_url())
    

# Upload reports
@login_required
def upload_reports(request,cid):
    '''upload_reports to a collection (currently not implemented)
    '''
    collection = get_report_collection(cid)
    messages.info(request,"Upload of reports in the interface is not currently supported.")    
    return view_report_collection(request,cid)


# Edit report collection
@login_required
def edit_report_collection(request, cid=None):

    if cid:
        collection = get_report_collection(cid)
    else:
        collection = ReportCollection(owner=request.user)
        if has_collection_edit_permission(request,collection):

            if request.method == "POST":
                form = ReportCollectionForm(request.POST,instance=collection)
                if form.is_valid():
 
                    # Update annotators and contributors
                    previous_contribs = set()
                    previous_annots = set()
                    if form.instance.id is not None:
                        previous_contribs = set(form.instance.contributors.all())
                        previous_annots = set(form.instance.annotators.all())

                    collection = form.save(commit=False)
                    collection.save()

                    form.save_m2m()  # save contributors

                return HttpResponseRedirect(collection.get_absolute_url())
        else:
            form = ReportCollectionForm(instance=collection)

        edit_permission = has_collection_edit_permission(request,collection)
        context = {"form": form,
                   "edit_oermission": edit_permission}

        return render(request, "reports/edit_report_collection.html", context)

    # If user makes it down here, does not have permission
    messages.info(request, "You don't have permission to edit this collection.")
    return redirect("report_collections")



###############################################################################################
# Filter Sessions #############################################################################
###############################################################################################

@login_required
def create_annotation_session(request,cid):
    '''create_annotation_session will allow the user to create a custom annotation set
    (stored in a session) for making annotations. (not currently in use)
    :param cid: the collection id to use
    '''
    collection = get_report_collection(cid)
    if has_collection_edit_permission(request,collection):
        report_set = request.session.get('reports', None) 
        if report_set != None:
            if len(report_set) != 0:
                messages.warning(request, 'You have an annotation session in progress. Creating a new set will override it.')

        # Get collection annotators
        users = get_collection_users(collection)

        allowed_annotations = get_allowed_annotations(collection,return_objects=False)
        context = {"users": users,
                   "collection": collection,
                   "allowed_annotations": allowed_annotations}
        return render(request, "reports/create_annotation_set_local.html", context)
    return view_report_collection(request,cid)

@login_required
def save_annotation_session(request,cid):
    '''save_annotation_session will save the annotation set, meaning creation of 
    a session with the queryset. (not in use)
    :param cid: the collection id to use
    '''
    collection = get_report_collection(cid)
    if has_collection_edit_permission(request,collection):
        if request.method == "POST":

            # What user does the request want to see annotations by?
            user_id = request.POST.get('user')
            user = get_user(request,user_id)

            # What annotation (name and label) do we filter to?
            selection_keys = [x for x in request.POST.keys() if re.search("^whatisit[||]", x)]
            selections = []
            seen_annotations = []
            for selection_key in selection_keys:
                name,label = selection_key.replace("whatisit||","").split("||")
                annotation_object = AllowedAnnotation.objects.get(name=name,
                                                                      label=label)

                # Query to select the reports of interest
                selection = Annotation.objects.filter(annotator=user,
                                                      annotation=annotation_object,
                                                      reports__collection=collection)
                for annotation in selection:
                    if annotation not in seen_annotations:
                        selections = list(chain(selections,annotation.reports.all()))
                        seen_annotations.append(annotation)

            request.session['reports'] = selections
            return annotate_session(request,cid)

    return view_report_collection(request,cid)

@login_required
def annotate_session(request,cid):
    '''annotate_custom will allow the user to annotate a custom selected set (saved in a session)
    if not defined, the user is redirected to create one, with a message
    '''
    collection = get_report_collection(cid)
    if has_collection_edit_permission(request,collection):
        report_set = request.session.get('reports', None)

        # Undefined session means the user hasn't created a set yet
        if report_set == None:
            messages.info(request, 'You need to create an annotation set first.')   
            return create_annotation_set(request,cid)

        # The user has finished annotating all reports, time to move on.      
        elif len(report_set) == 0:
            return create_annotation_set(request,cid)
      
        # The user has reports left to annotate
        else:
            next_report = report_set.pop(0)
            request.session['reports'] = report_set
            return annotate_report(request,
                                   rid=next_report.id,
                                   report=next_report,
                                   next="set")

    return view_report_collection(request,cid)



###############################################################################################
# Filter Sets #################################################################################
###############################################################################################

@login_required
def create_annotation_set(request,cid):
    '''create_annotation_set will allow the user to create a custom annotation set
    (stored as ReportSet) for making annotations.
    :param cid: the collection id to use
    '''
    collection = get_report_collection(cid)
    if has_collection_edit_permission(request,collection):
        users = get_collection_annotators(collection)
        allowed_annotations = get_allowed_annotations(collection,return_objects=False)

        # Only allow generation of a set if minimum of 25 reports (for gold standard)
        count = get_annotation_counts(collection)['total']
        if count < GOLD_STANDARD_MIN_ANNOTS:
            messages.info(request,'''You must have a minimum of 25 annotations to create an annotation set. 
                                     A collection owner or contributor can annotate random reports to generate 
                                     this gold standard.''')
            return view_report_collection(request,cid)


        context = {"users": users,
                   "collection": collection,
                   "allowed_annotations": allowed_annotations}
        return render(request, "reports/create_annotation_set.html", context)
    return view_report_collection(request,cid)


@login_required
def save_annotation_set(request,cid):
    '''save_annotation_set will save the annotation set, meaning creation of 
    a ReportSet with the queryset.
    :param cid: the collection id to use
    '''
    collection = get_report_collection(cid)
    if has_collection_edit_permission(request,collection):
        if request.method == "POST":
            
            # What does the user want to name the set?
            set_name = request.POST.get('setname').lower().replace(" ","_")

            # What user should be used as gold standard?
            gold_standard = request.POST.get('gold_standard')

            # How many reports in the set?
            request,N = parse_numeric_input(request=request,
                                            value=request.POST.get('N'),
                                            default=100,
                                            description="the number of reports")
            
            # How many tests should be given and passing?
            request,testing_set = parse_numeric_input(request=request,
                                                      value=request.POST.get('testing_set'),
                                                      default=25,
                                                      description="the number of testing reports")

            request,testing_set_correct = parse_numeric_input(request=request,
                                                              value=request.POST.get('testing_set_correct'),
                                                              default=20,
                                                              description="the number reports correct to pass")

            # Required number correct must be less than total
            if testing_set_correct > testing_set:
                messages.info(request,"The required number of passing questions must be less than or equal to the number of testing questions.")
                return create_annotation_set(request,cid)

            # What users does the request want to see annotations by?
            user_id = request.POST.get('user')
            if user_id == 'all':
                user = [u.id for u in get_collection_users(collection)]
            else:
                user = [get_user(request,user_id).id]

            # What annotation (name and label) do we filter to?
            selection_keys = [x for x in request.POST.keys() if re.search("^whatisit[||]", x)]
            generate_annotation_set.apply_async(kwargs={'uid':request.user.id,
                                                        'user_ids':user,
                                                        'selection_keys':selection_keys,
                                                        'cid':collection.id,
                                                        'N':N,
                                                        'testing_set':testing_set,
                                                        'testing_set_correct':testing_set_correct,
                                                        'gid':gold_standard,
                                                        'set_name':set_name})

            messages.info(request,"""Your set is being created. It's status will be sent via notification. Once it is created, you should add annotators to it.""")

    return redirect('report_collection_details',cid=collection.id)


@login_required
def annotate_set(request,sid,show_count=True):
    '''annotate_set will allow the user to annotate a custom selected set
    '''
    report_set = get_report_set(sid)
    collection = report_set.collection
    user = request.user

    # Only continue annotation if the user is approved (and not expired)
    user_status = get_annotation_status(report_set=report_set,
                                        user=user) 

    # No credential exists, for user (this should not happen)
    if user_status == None:
        messages.info(request,"You must ask for permission to annotate a collection first.")
        return view_report_collection(request,report_set.collection.id)

    # Approved means we continue
    if user_status == "PASSED":
        
        if has_collection_annotate_permission(request,collection):

            # If the user has un-annotated reports, return those first
            reports = report_set.reports.all().exclude(reports_annotated__annotator=user).distinct()
            if len(reports) == 0:
                reports = report_set.reports.all()
            return annotate_random(request,
                                   cid=collection.id,
                                   sid=sid,
                                   reports=reports)


    elif user_status == "TESTING":
        # Send the user to the testing view, will grant permission/deny after test
        return test_annotator(request=request,
                              sid=report_set.id)

    else: #denied or other
        messages.info(request,"You are not allowed to perform this action.")
        return view_report_collection(request,report_set.collection.id)


###############################################################################################
# Bulk Annotation #############################################################################
###############################################################################################


@login_required
def bulk_annotate(request,cid,sid=None):
    '''bulk annotate will allow a user to apply annotations, in masse, to a collection or set
    :param cid: the collection id to use
    :param sid: the report set id, if a subset of reports is being used
    '''
    if sid !=None:
        report_set = get_report_set(sid)
        collection = report_set.collection
        reports = report_set.reports.all()
    else:
        collection = get_report_collection(cid)
        reports = collection.report_set.all()
   
    if has_collection_edit_permission(request,collection):

        # POST indicates creating a bulk annotation
        if request.method == "POST":

            # Does the user want to bulk annotate only unlabeled sets?
            unlabeled_only = request.POST.get('unlabeled_only',None)

            # What annotations does the user want to do in bulk?
            selection_keys = [x for x in request.POST.keys() if re.search("^whatisit[||]", x)]
            selections = []
            seen_annotations = []
            for selection_key in selection_keys:
                name = selection_key.replace("whatisit||","")
                label = request.POST.get(selection_key,"")
                if label != "":
                    
                    allowed_annotation = AllowedAnnotation.objects.get(name=name,
                                                                       label=label)

                    # If the user doesn't want to include already labeled reports, exclude
                    if unlabeled_only != None:
                        reports = reports.exclude(reports_annotated__annotator=request.user).distinct()

                    for report in reports:
                        # Update user annotation sent to celery to run async
                        update_user_annotation.apply_async(kwargs={'user':request.user.id, 
                                                                   'allowed_annotation':allowed_annotation.id,
                                                                   'report':report.id})

                    messages.info(request,"Annotation %s:%s task running for %s reports" %(name,label,reports.count()))
        
                return view_report_collection(request,cid)

        # Otherwise just render the form
        else:

            allowed_annotations = get_allowed_annotations(collection,return_objects=False)

            context = {"collection": collection,
                       "allowed_annotations": allowed_annotations}

            if sid != None:
                context['sid'] = sid

            return render(request, "annotate/bulk_annotate.html", context)
    return view_report_collection(request,cid)
        


###############################################################################################
# Labels ######################################################################################
###############################################################################################

def view_label(request,cid,template=None):
    '''view_label is a general template to return a view of labels
    '''
    collection = get_report_collection(cid)
    if template==None:
        template = 'labels/new_collection_label.html'

    # Labels associated with collection
    collection_labels = collection.allowed_annotations.all()
    labels = [x for x in AllowedAnnotation.objects.all() if x not in collection_labels]

    context = {'labels':labels,
               'collection':collection,
               'collection_labels':collection_labels}

    # send back json response success
    return render(request, template, context)


@login_required
def create_label(request,cid,lid=None):
    '''create_label will allow a user to create a new label to be associated with a collection. The user
    will be able to select from other collection labels
    :param cid: the collection id to associate the label with (not required, but no url accessible for it) 
    :param lid: if provided on a post, the label will be added to the collection as an allowed annotation
    '''
    collection = get_report_collection(cid)

    if request.user == collection.owner:

        if request.method == "POST":

            # If lid is defined, we are adding an already existing annotation label to collection
            if lid != None:
                try:
                    allowed_annotation = AllowedAnnotation.objects.get(id=lid)
                    collection.allowed_annotations.add(allowed_annotation)
                    collection.save()
                    label_name = "%s:%s" %(allowed_annotation.name,
                                           allowed_annotation.label)
                    response_text = {"result": "New annotation label %s added successfully." %(label_name)}

                except BaseException as e:
                    response_text = {"error": "Error retrieving allowed annotation %s, %s" %(lid,e.message)}

            # Otherwise, the user wants a new one
            else:

                name = request.POST.get('annotation_name', None)
                if name != None:
                    for key in request.POST.keys():
                        if re.search('annotation_label',key):
                            new_label = request.POST.get(key)
                            allowed_annot,created = AllowedAnnotation.objects.get_or_create(name=name,
                                                                                         label=new_label)                       
                            if created == True:
                                allowed_annot.save()
                            collection.allowed_annotations.add(allowed_annot)

                    messages.info(request,"Label generation successful.")
                else:
                    messages.info(request,"An annotation name is required.")
                
                return view_label(request,cid)

        else:

            return view_label(request,cid)

        return JsonResponse(response_text)

    else:
        # Does not have permission, return to collection
        messages.info(request, "You do not have permission to perform this action.")
    return view_report_collection(request,cid)




###############################################################################################
# annotations #################################################################################
###############################################################################################

@login_required
def annotate_report(request,rid,sid=None,report=None,next=None,template=None,
                    allowed_annotations=None,show_count=True):
    '''annotate_report is the view to return a report annotation interface for a particular report id
    :param rid: report id to annotate
    :param sid: a report set id, if coming from annotate_random with a report set
    :param report_set: a report set.
    :param show_count: if true, will show the user the total reports annotated
    :param next: the next page to show (annotate/reports/{{ collection.id }}/{{ next }}
    :param template: an optional template, if not provided, default is used
    :param allowed_annotations: a custom set of allowed annotations to use. If not provided,
    the entire set of a collection is used.
    '''
    if report == None:
        report = get_report(rid)
    collection = report.collection

    if template == None:
        template = "annotate/annotate_random.html"

    context = {"collection":collection,
               "report":report}

    if sid != None:
        next = "%s/set" %(sid)
        context['sid'] = sid

    # If next is None, return random
    elif next == None:
        next = "%s/random" %(collection.id)

    # If it's not None, we still need to add collection id
    else:
        next = "%s/%s" %(collection.id,next)

    # Tell the user how many annotated / remaining
    if show_count == True:
        remaining_message = count_remaining_reports(user=request.user,
                                                    collection=collection,
                                                    sid=sid,
                                                    return_message=True)
        messages.info(request,remaining_message)


    # Next url will direct to either set, or random
    context['next'] = next

    # Get the concise annotations
    annotations = get_annotations(user=request.user, report=report)
    annotations = summarize_annotations(annotations)
    if "labels" in annotations:
        context["annotations"] = annotations['labels']
    if "counts" in annotations:
        context["counts"] = annotations['counts']

    # Get the allowed_annotations, and organize them into a lookup dictionary with key:options
    if allowed_annotations == None:
        allowed_annotations = report.collection.allowed_annotations.all()
    context["allowed_annotations"] = group_allowed_annotations(allowed_annotations)

    # Format markup
    context["markup"] = ["%s" %(x) for x in report.collection.markup.split(",")]  

    # Get all permissions, context must have collection as key
    context = get_permissions(request,context)

    return render(request, template, context)


@login_required
def clear_annotations(request,rid,report=None):
    '''clear all annotations for a specific report and user'''

    if report == None:
        report = get_report(rid)

    # Right now, only owners allowed to contribute
    annotate_permission = has_collection_annotate_permission(request,report.collection)
    if annotate_permission:

        if request.method == 'POST':
            try:
                clear_user_annotations(request.user,report)
                response_data = {'result':'Annotations successfully cleared'}
            except:
                response_data = {'result':'Error clearing annotations.'}

            return JsonResponse(response_data)

        else:
            return JsonResponse({"have you ever seen...": "a radiologist rigatoni?"})

    else:
        context = {"message":"You are not authorized to perform this action"}
        return render(request, "messages/not_authorized.html", context)


@login_required
def update_annotation(request,rid,report=None):
    '''update_annotation is the view to update an annotation when it changes. It should return a JSON response.
    '''
    if report == None:
        report = get_report(rid)

    # Does the user have permission to annotate the collection?
    annotate_permission = has_collection_annotate_permission(request,report.collection)
    if annotate_permission:

        if request.method == 'POST':
            try:
                new_annotations = json.loads(request.POST.get('annotations'))
            
            except:
                return JsonResponse({"error": "error parsing array!"})

            # Update the annotations
            for new_annotation in new_annotations:
                if new_annotation['value'] == "on":
                    aname,alabel = new_annotation['name'].split('||')
                    annotation_object = AllowedAnnotation.objects.get(name=aname,
                                                                      label=alabel)
                    annot = update_user_annotation(user=request.user,
                                                   allowed_annotation=annotation_object,
                                                   report=report)

            response_data = {'result':'Create post successful!'}

            return JsonResponse(response_data)

        else:
            return JsonResponse({"have you ever seen...": "a radiologist ravioli?"})

    else:
        context = {"message":"You are not authorized to annotate this collection."}
        return render(request, "messages/not_authorized.html", context)


@login_required
def annotate_random(request,cid,rid=None,sid=None,reports=None):
    '''annotate_random will select a random record from a collection, and render a page for
    the user to annotate
    :param cid: the collection id to select from
    :param rid: a report id, if provided, to annotate
    :param sid: the set id of a report, if provided, will be sent in with the next url param
    :param reports: a pre selected subset to select randomly from
    '''
    collection = get_report_collection(cid)
    if reports == None:
        reports = Report.objects.filter(collection=collection)

    # Get a random report (if gets slow, change to get_random_report
    report = select_random_reports(reports)[0]

    # Ensure url returned is for report
    if sid != None:
        return HttpResponseRedirect(reverse('annotate_report',  kwargs={'rid': report.id, 
                                                                        'sid': sid}))
    return HttpResponseRedirect(reverse('annotate_report',  kwargs={'rid': report.id}))



############################################################################################
# TESTING ##################################################################################
############################################################################################

@login_required
def annotate_testing(request,cid,rid=None,sid=None,reports=None):
    '''annotate_random will select a random record from a collection, and render a page for
    the user to annotate
    :param cid: the collection id to select from
    :param rid: a report id, if provided, to annotate
    :param sid: the set id of a report, if provided, will be sent in with the next url param
    :param reports: a pre selected subset to select randomly from
    '''
    collection = get_report_collection(cid)
    if reports == None:
        reports = Report.objects.filter(collection=collection)

    # Get a random report (if gets slow, change to get_random_report
    report = select_random_reports(reports)[0]

    # Ensure url returned is for report
    if sid != None:
        return HttpResponseRedirect(reverse('annotate_report_testing',  kwargs={'rid': report.id,
                                                                                'sid': sid}))
    return HttpResponseRedirect(reverse('annotate_report_testing',  kwargs={'rid': report.id}))


@login_required
def annotate_report_testing(request,rid,sid=None,report=None,next=None,allowed_annotations=None):
    '''annotate_report_testing is the view to return a report annotation interface to test an id
    :param sid: a report set id, if coming from annotate_random with a report set
    :param report_set: a report set.
    :param next: the next page to show (annotate/reports/{{ collection.id }}/{{ next }}
    :param allowed_annotations: a custom set of allowed annotations to use. If not provided,
    the entire set of a collection is used.
    '''
    if report == None:
        report = get_report(rid)
    collection = report.collection

    context = {"collection":collection,
               "report":report}

    if sid != None:
        next = "%s/set" %(sid)
        context['sid'] = sid

    # If next is None, return random
    elif next == None:
        next = "%s/random" %(collection.id)

    # If it's not None, we still need to add collection id
    else:
        next = "%s/%s" %(collection.id,next)

    # Next url will direct to either set, or random
    context['next'] = next

    # Get the concise annotations
    annotations = get_annotations(user=request.user, report=report)
    annotations = summarize_annotations(annotations)
    if "labels" in annotations:
        context["annotations"] = annotations['labels']
    if "counts" in annotations:
        context["counts"] = annotations['counts']

    # Get the allowed_annotations, and organize them into a lookup dictionary with key:options
    if allowed_annotations == None:
        allowed_annotations = report.collection.allowed_annotations.all()
    context["allowed_annotations"] = group_allowed_annotations(allowed_annotations)

    # Format markup
    context["markup"] = ["%s" %(x) for x in report.collection.markup.split(",")]  

    # Get all permissions, context must have collection as key
    context = get_permissions(request,context)

    return render(request, "annotate/testing_random.html", context)
