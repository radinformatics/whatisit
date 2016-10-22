from whatisit.apps.labelinator.forms import (ReportForm, ReportCollectionForm)
from whatisit.apps.labelinator.models import Report, ReportCollection, Annotation, AllowedAnnotation
from whatisit.apps.labelinator.utils import get_annotation_counts, add_message, group_allowed_annotations, \
   summarize_annotations
from whatisit.settings import BASE_DIR, MEDIA_ROOT

from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.decorators import login_required
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

# need functions here to check permissions of things, after add users

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

# All reports
def all_reports(request):
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
               "page_title":"My report Collections"}
    return render(request, 'reports/all_reports.html', context)

# View report collection
@login_required
def view_report_collection(request,cid):
    collection = get_report_collection(cid,request)
    # Get a count of annotations by label in the collection
    annotation_counts = get_annotation_counts(collection)
    report_count = Report.objects.filter(collection=collection).count()
    context = {"collection":collection,
               "annotation_counts":annotation_counts,
               "report_count":report_count}
    return render(request, 'reports/report_collection_details.html', context)

# View report
#TODO: this will be the file/guts of the report, not done yet
@login_required
def view_report(request,cid):
    report = get_report(cid,request)
    context = {"report":report}
    return render(request, 'reports/report_details.html', context)

# Delete report
@login_required
def delete_report(request,cid):
    report = get_report(cid,request)
    collection = report.collection
    if request.user == collection.owner:
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
    if collection.owner == request.user:

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
    annotations = Annotation.objects.filter(reports__report_id=report.report_id).annotate(Count('annotation', distinct=True))
    annotations = summarize_annotations(annotations)

    # Get the allowed_annotations, and organize them into a lookup dictionary with key:options
    allowed_annotations = report.collection.allowed_annotations.all()
    allowed_annotations = group_allowed_annotations(allowed_annotations)

    context = {"report":report,
               "annotations":annotations['labels'],
               "counts":annotations['counts'],
               "collection":report.collection,
               "allowed_annotations":allowed_annotations}

    return render(request, "annotate/annotate_random.html", context)


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
def annotate_curated(request,cid):
    return render(request, "annotate/annotate_curated.html", context)


@login_required
def annotate_custom(request,cid):
    return render(request, "annotate/annotate_custom.html", context)



