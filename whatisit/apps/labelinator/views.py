from whatisit.apps.labelinator.forms import (ReportForm, ReportCollectionForm)
from whatisit.apps.labelinator.models import Report, ReportCollection, Annotation, AllowedAnnotation
from whatisit.apps.labelinator.utils import get_annotation_counts, add_message, group_allowed_annotations, \
   summarize_annotations, get_annotations, update_user_annotation
from whatisit.settings import BASE_DIR, MEDIA_ROOT
from whatisit.apps.users.models import RequestMembership

from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models.aggregates import Count
from django.forms.models import model_to_dict
from django.http import HttpResponse, JsonResponse
from django.http.response import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, render_to_response, render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.utils import timezone
from django.urls import reverse

import csv
import datetime
import gzip
import hashlib
import json
import os
import numpy
import pandas
import pickle
from random import randint
import re
import shutil
import tarfile
import tempfile
import traceback
import uuid
import zipfile

media_dir = os.path.join(BASE_DIR,MEDIA_ROOT)

### AUTHENTICATION ####################################################

@login_required
def get_permissions(request,context):
    '''get_permissions returns an updated context with edit_permission and annotate_permission
    for a user. The key "collection" must be in the context
    '''
    collection = context["collection"]

    # Edit and annotate permissions?
    context["edit_permission"] = has_collection_edit_permission(request,collection)
    context["annotate_permission"] = has_collection_annotate_permission(request,collection)
    
    # If no annotate permission, get their request
    if context["annotate_permission"] == False:
        try:
            context['membership'] = RequestMembership.objects.get(requester=request.user,
                                                                  collection=collection)
        except:
            pass
    return context


# Does a user have permissions to see a collection?

def has_collection_edit_permission(request,collection):
    if request.user == collection.owner:
        return True
    return False

def has_collection_annotate_permission(request,collection):
    if has_collection_edit_permission(request,collection):
        return True
    if request.user in collection.contributors.all():
        return True
    return False

@login_required
def request_annotate_permission(request,cid):    
    '''request_annotate_permission will allow a user to request addition to
    a collection (as an annotator) via a RequestMembership object
    '''
    collection = get_report_collection(cid,request)
    previous_request,created = RequestMembership.objects.get_or_create(requester=request.user,
                                                                       collection=collection)
    if created == True:
        previous_request.save()

    # redirect back to collection with message
    messages.success(request, 'Request sent.')
    return view_report_collection(request,cid)


@login_required
def deny_annotate_permission(request,cid,uid):
    collection = get_report_collection(cid,request)
    if has_collection_edit_permission(request,collection):
        requester = User.objects.get(id=uid)
        permission_request = RequestMembership.objects.get(collection=collection,
                                                           requester=requester)
        if permission_request.status not in ["APPROVED","DENIED"]:
            permission_request.status = "DENIED"
            permission_request.save()
            messages.success(request, 'Contributors updated.')    
    return view_report_collection(request,cid)


@login_required
def approve_annotate_permission(request,cid,uid):
    collection = get_report_collection(cid,request)
    if has_collection_edit_permission(request,collection):
        requester = User.objects.get(id=uid)
        permission_request = RequestMembership.objects.get(collection=collection,
                                                           requester=requester)
        if permission_request.status not in ["APPROVED","DENIED"]:
            collection.contributors.add(requester)
            collection.save()
            permission_request.status = "APPROVED"
            permission_request.save()
            messages.success(request, 'Contributors approved.')
    
    return view_report_collection(request,cid)


#### GETS #############################################################

# get report
def get_report(cid,request):
    keyargs = {'id':cid}
    try:
        report = Report.objects.get(**keyargs)
    except Report.DoesNotExist:
        raise Http404
    else:
        return report

# get report collection
def get_report_collection(cid,request):
    keyargs = {'id':cid}
    try:
        collection = ReportCollection.objects.get(**keyargs)
    except ReportCollection.DoesNotExist:
        raise Http404
    else:
        return collection

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
    collection = get_report_collection(cid,request)
    report_count = Report.objects.filter(collection=collection).count()
    context = {"collection":collection,
               "report_count":report_count}

    # Get all permissions, context must have collection as key
    context = get_permissions(request,context)

    # If the user has edit_permissions, we want to show him/her users that can be added
    if context["edit_permission"] == True:
        context["requesters"] = RequestMembership.objects.filter(collection=collection)
        context["requesters_pending"] = len([x for x in context["requesters"] if x.status == "PENDING"])

    return render(request, 'reports/report_collection_details.html', context)


@login_required
def save_collection_markup(request,cid):
    collection = get_report_collection(cid,request)
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
    collection = get_report_collection(cid,request)
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
    report = get_report(rid,request)
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
def delete_report(request,cid):
    report = get_report(cid,request)
    collection = report.collection
    edit_permission = has_collection_edit_permission(request,collection)
    if edit_permission:
        if report.image.file != None:
            file_path = report.image.file.name
            if os.path.exists(file_path):
                os.remove(file_path)
        report.delete()
    else:
        # If not authorizer, alert!
        msg = "You are not authorized to perform this operation."
        messages.warning(request, msg)
    return HttpResponseRedirect(collection.get_absolute_url())
    

# Edit report
@login_required
def edit_report(request,coid,cid=None):

    # TODO: Add collaborators checking
    collection = get_report_collection(coid,request)
    edit_permission = has_collection_edit_permission(request,collection)
    if edit_permission:

        # Has the user provided a report?
        #TODO: make report file/upload view here, we shouldn't
        # be able to edit an individual report!
        if cid != None:
            report = get_report(cid,request)
        else:
            report = Report()

        if request.method == "POST":
            form = reportForm(request.POST,instance=report)
            if form.is_valid():
                report = form.save(commit=False)
                report.save()
                return HttpResponseRedirect(report.get_absolute_url())
        else:
            form = reportForm(instance=report)
            context = {"form": form,
                       "collection": collection}
            return render(request, "reports/edit_report.html", context)
    return redirect("report_collections")


# Edit report collection
@login_required
def edit_report_collection(request, cid=None):

    if cid:
        collection = get_report_collection(cid,request)
        is_owner = collection.owner == request.user
    else:
        is_owner = True
        collection = ReportCollection(owner=request.user)
        if request.method == "POST":
            form = ReportCollectionForm(request.POST,instance=collection)
            if form.is_valid():
                previous_contribs = set()
                if form.instance.id is not None:
                    previous_contribs = set(form.instance.contributors.all())
                collection = form.save(commit=False)
                collection.save()

                if is_owner:
                    form.save_m2m()  # save contributors
                    current_contribs = set(collection.contributors.all())
                    new_contribs = list(current_contribs.difference(previous_contribs))

                return HttpResponseRedirect(collection.get_absolute_url())
        else:
            form = ReportCollectionForm(instance=collection)

        context = {"form": form,
                   "is_owner": is_owner}

        return render(request, "reports/edit_report_collection.html", context)
    return redirect("report_collections")


# Upload reports
@login_required
def upload_report(request,cid):
    collection = get_report_collection(cid,request)
    is_owner = collection.owner == request.user
    if is_owner:
        if request.method == 'POST':
            form = reportForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    if 'image' in request.FILES:
                        image_name = request.FILES["image"].name
                        # DO PARSING OF report META FROM HEADER HERE
                        # Save image file to server, and to new report model
                        report = save_image_upload(collection,request.FILES['image'])
                        # Redirect user to view to specify inputs and outputs (boutiques spec)
                        message = "Please define input and output specifications to use your report!"
                        messages.warning(request, message)
                        return redirect('edit_report_specs', cid=report.id)
                    else:
                        raise Exception("Unable to find uploaded files.")
                except:
                    error = traceback.format_exc().splitlines()
                    msg = "An error occurred with this upload: {}".format(error)
                    messages.warning(request, msg)
                
            return HttpResponseRedirect(collection.get_absolute_url())
        else:
            form = reportForm()
            context = {"form": form,
                       "collection": collection}
            return render(request, "reports/edit_report.html", context)


###############################################################################################
# annotations #################################################################################
###############################################################################################

@login_required
def annotate_report(request,rid,report=None):
    '''annotate_report is the view to return a report annotation interface for a particular report id
    :param rid: report id to annotate
    '''
    if report == None:
        report = get_report(rid,request)

    # Get the concise annotations
    annotations = get_annotations(user=request.user, report=report)
    annotations = summarize_annotations(annotations)

    # Get the allowed_annotations, and organize them into a lookup dictionary with key:options
    allowed_annotations = report.collection.allowed_annotations.all()
    allowed_annotations = group_allowed_annotations(allowed_annotations)

    # Format markup
    markup = ["%s" %(x) for x in report.collection.markup.split(",")]  

    context = {"report":report,
               "annotations":annotations['labels'],
               "counts":annotations['counts'],
               "collection":report.collection,
               "markup":markup,
               "allowed_annotations":allowed_annotations}

    # Get all permissions, context must have collection as key
    context = get_permissions(request,context)

    return render(request, "annotate/annotate_random.html", context)


@login_required
def update_annotation(request,rid,report=None):
    '''update_annotation is the view to update an annotation when it changes. It should return a JSON response.
    '''
    if report == None:
        report = get_report(rid,request)

    # Right now, only owners allowed to contribute
    annotate_permission = has_collection_annotate_permission(request,report.collection)
    if annotate_permission:

        # Get the concise annotations (not sure if I need these, actually)        
        annotations = get_annotations(user=request.user, report=report)

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
                                                   annotation_object=annotation_object,
                                                   report=report)

            response_data = {}
            response_data['result'] = 'Create post successful!'

            return JsonResponse(response_data)

        else:
            return JsonResponse({"have you ever seen...": "a radiologist ravioli?"})

    else:
        context = {"message":"You are not authorized to annotate this collection."}
        return render(request, "messages/not_authorized.html", context)


@login_required
def annotate_random(request,cid,rid=None):
    '''annotate_random will select a random record from a collection, and render a page for
    the user to annotate
    :param cid: the collection id to select from
    :param rid: a report id, if provided, to annotate
    '''
    collection = get_report_collection(cid,request)

    # Get a random report
    while rid == None:
        count = Report.objects.filter(collection=collection).aggregate(count=Count('id'))['count']
        rid = randint(0, count - 1)
        try:
            record = Report.objects.get(id=rid)
        except:
            rid = None

    # Ensure url returned is for report
    return HttpResponseRedirect(reverse('annotate_report', args=(rid,)))
    

@login_required
def annotate_custom(request,cid):
    return annotate_random(request,cid)
    #return render(request, "annotate/annotate_custom.html", context)


@login_required
def annotate_curated(request,cid):
    return annotate_random(request,cid)
    #return render(request, "annotate/annotate_curated.html", context)
