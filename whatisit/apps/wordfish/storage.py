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

import pandas
import errno
import itertools
import os
import tempfile

############################################################################
# Storage Models
############################################################################

class WhatisitStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None):
        if location is None:
            location = MEDIA_ROOT
        if base_url is None:
            base_url = MEDIA_URL
        super(WhatisitStorage, self).__init__(location, base_url)

    def url(self, name):
        uid = None
        spath, file_name = os.path.split(name)
        urlsects = [v for v in spath.split('/') if v]
        for i in range(len(urlsects)):
            sect = urlsects.pop(0)
            if sect.isdigit():
                collection_id = sect
                break
        report_path = '/'.join(urlsects)
        coll_model = apps.get_model('whatisit', 'ReportCollection')
        collection = coll_model.objects.get(id=uid)
        #if collection.private:
        #    cid = collection.private_token
        #else:
        cid = collection.id
        return os.path.join(self.base_url, str(cid), cont_path, file_name)


class ImageStorage(WhatisitStorage):
    def get_available_name(self, name):
        """
        Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        """
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        # If the filename already exists, add an underscore and a number (before
        # the file extension, if one exists) to the filename until the generated
        # filename doesn't exist.
        count = itertools.count(1)
        while self.exists(name):
            # file_ext includes the dot.
            name = os.path.join(dir_name, "%s_%s%s" % (file_root, next(count), file_ext))

        return name


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
        user = User.objects.get(uid)
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
        context = {"annotators":get_collection_annotators(collection),
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
