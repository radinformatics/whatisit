from django.http import (
    HttpResponse,
    JsonResponse
)

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

from django.core.files.storage import FileSystemStorage
from django.core.files.move import file_move_safe
from django.contrib.auth.models import User
from django.apps import apps

from fnmatch import fnmatch
from whatisit.settings import (
    MEDIA_ROOT, 
    MEDIA_URL
)

from whatisit.apps.wordfish.utils import (
    get_collection_annotators,
    get_report_collection,
    get_report_set,
    get_reportset_annotations    
)

from whatisit.apps.wordfish.models import ReportSet

import pandas
import errno
import itertools
import os
import tempfile


############################################################################
# Exporting Data
############################################################################

def download_annotation_set_json(request,sid,uid):
    '''a wrapper view for download annotation_set, setting return_json to True
    :param sid: the report set id
    :param uid: the user id to download
    '''    
    return download_annotation_set(request,sid,uid,return_json=True)


def download_annotation_set(request,sid,uid,return_json=False):
    '''download annotation set will download annotations for a particular user
    and report set. Default returns a text/csv file, if return_json is true,
    returns json file
    :param sid: the report set id
    :param uid: the user id to download
    :param return_json: return a Json response instead (default is False)
    '''
    report_set = get_report_set(sid)
    collection = report_set.collection

    # Does the user have permission to edit?
    requester = request.user
    if requester == collection.owner or requester in collection.contributors.all():
        user = User.objects.get(id=uid)
        df = get_reportset_annotations(report_set,user)
        if not return_json:
            response = HttpResponse(df.to_csv(sep="\t"), content_type='text/csv')
            export_name = "%s_%s_annotations.tsv" %(report_set.id,user.username)
            response['Content-Disposition'] = 'attachment; filename="%s"' %(export_name)
            return response
        return JsonResponse(df.to_json(orient="records"))    

    messages.info(request,"You do not have permission to perform this action.")
    return redirect('report_collection_details',cid=collection.id)


def download_data(request,cid):
    '''download data returns a general view for a collection to download data,
    meaning all reports, reports for a set, or annotations for a set
    :param cid: the collection id
    '''
    collection = get_report_collection(cid)

    # Does the user have permission to edit?
    requester = request.user
    if requester == collection.owner or requester in collection.contributors.all():
        context = {"collection":collection,
                   "annotators":get_collection_annotators(collection),
                   "report_sets":ReportSet.objects.filter(collection=collection)}
        return render(request, 'export/download_data.html', context)

    messages.info(request,"You do not have permission to perform this action.")
    return redirect('report_collection_details',cid=collection.id)


def download_reports_json(request,cid,sid=None):
    '''download_reports_json is a wrapper for download_reports, ensuring
    that a json response is returned
    :param cid: the collection id
    :param sid: the report set if, if provided use that report set.
    '''
    return download_reports(request,cid,sid=sid,return_json=True)


def download_reports(request,cid,sid=None,return_json=False):
    '''download reports returns a tsv download for an entire collection of reports (not recommended)
    or for reports within a collection (recommended)
    :param cid: the collection id
    :param sid: the report set if, if provided use that report set.
    :param return_json: return a Json response instead (default is False)
    '''
    if sid != None:
        report_set = get_report_set(sid)
        collection = report_set.collection
        reports = report_set.reports.all()
        export_name = "%s_reports_set.tsv" %(report_set.id)
    else:
        collection = get_report_collection(cid)
        reports = collection.report_set.all()
        export_name = "%s_reports.tsv" %(collection.id)

    # Does the user have permission to edit?
    requester = request.user
    if requester == collection.owner or requester in collection.contributors.all():
        df = pandas.DataFrame(columns=["report_id","report_text"])
        df["report_id"] = [r.report_id for r in reports]
        df["report_text"] = [r.report_text for r in reports]
        if not return_json:
            response = HttpResponse(df.to_csv(sep="\t"), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="%s"' %(export_name)
            return response
        else:
            return JsonResponse(df.to_json(orient="records"))

    messages.info(request,"You do not have permission to perform this action.")
    return redirect('report_collection_details',cid=collection.id)
