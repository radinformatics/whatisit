from notifications.signals import notify
from whatisit.apps.tagtrout.forms import (
    docForm, 
    docCollectionForm,
)

from whatisit.apps.tagtrout.models import (
    Doc,
    DocCollection,
)


# STOPPED HERE - update these functions, then upload
from whatisit.apps.tagtrout.utils import (
    get_doc,
    get_docs_collection,
    select_random_doc,
    select_random_docs
)

from whatisit.settings import (
    BASE_DIR, 
    MEDIA_ROOT
)

from whatisit.apps.users.models import RequestMembership, Credential
from whatisit.apps.users.utils import (
    get_user
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



###############################################################################################
# Contributors ################################################################################
###############################################################################################

@login_required
def edit_contributors(request,did):
    '''edit_contributors is the view to see, add, and delete contributors for a set.
    '''
    collection = get_docs_collection(did)
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
        
        return render(request, 'docs/edit_collection_contributors.html', context)

    # Does not have permission, return to collection
    messages.info(request, "You do not have permission to perform this action.")
    return redirect('doc_collection_details',kwargs={'did':collection.id})


@login_required
def add_contributor(request,did):
    '''add a new contributor to a collection
    :param did: the collection id
    '''
    collection = get_docs_collection(did)
    if request.user == collection.owner:
        if request.method == "POST":
            user_id = request.POST.get('user',None)
            if user_id:
                user = get_user(request,user_id)
                collection.contributors.add(user)
                collection.save()

                # Alert the user of the status change
                message = """You have been added as a contributor to the %s.""" %(collection.name)
                notify.send(collection.owner, recipient=user, verb=message)

                messages.success(request, 'User %s added as contributor to collection.' %(user))

    return edit_contributors(request,did)


@login_required
def remove_contributor(request,did,uid):
    '''remove a contributor from a collection
    :param did: the collection id
    :param uid: the contributor (user) id
    '''
    collection = get_doc_collection(did)
    user = get_user(request,uid)
    contributors = collection.contributors.all()
    if request.user == collection.owner:
        if user in contributors:    
            collection.contributors = [x for x in contributors if x != user]
            collection.save()
            messages.success(request, 'User %s is no longer a contributor to the collection.' %(contributor))

    return edit_contributors(request,did)



###############################################################################################
# docs ########################################################################################
###############################################################################################


# View all collections
def view_docs_collections(request):
    has_collections = False
    collections = DocsCollection.objects.filter(private=False)
    context = {"collections":collections,
               "page_title":"Document Collections"}
    return render(request, 'docs/all_docs.html', context)


# Personal collections
@login_required
def my_docs_collections(request):
    collections = DocsCollection.objects.filter(owner=request.user)
    context = {"collections":collections,
               "page_title":"My Collections"}
    return render(request, 'docs/all_docs.html', context)


# View doc collection
@login_required
def view_docs_collection(request,did):
    collection = get_docs_collection(did)
    doc_count = collection.doc_set.count()
    context = {"collection":collection,
               "doc_count":doc_count}

    # Get all permissions, context must have collection as key
    context = get_permissions(request,context)

    return render(request, 'docs/docs_collection_details.html', context)


# View doc
@login_required
def view_doc(request,did):
    doc = get_doc(did)

    context = {"doc":doc,
               "collection":docs.collection}

    # Get all permissions, context must have collection as key
    context = get_permissions(request,context)

    return render(request, 'docs/doc_details.html', context)
    

# Edit doc collection
@login_required
def edit_docs_collection(request, did=None):

    if did:
        collection = get_doc_collection(did)
    else:
        collection = docCollection(owner=request.user)
        if has_collection_edit_permission(request,collection):

            if request.method == "POST":
                form = docCollectionForm(request.POST,instance=collection)
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
            form = docCollectionForm(instance=collection)

        edit_permission = has_collection_edit_permission(request,collection)
        context = {"form": form,
                   "edit_oermission": edit_permission}

        return render(request, "docs/edit_doc_collection.html", context)

    # If user makes it down here, does not have permission
    messages.info(request, "You don't have permission to edit this collection.")
    return redirect("doc_collections")




@login_required
def annotate_random(request,did,rid=None,sid=None,docs=None):
    '''annotate_random will select a random record from a collection, and render a page for
    the user to annotate
    :param did: the collection id to select from
    :param rid: a doc id, if provided, to annotate
    :param sid: the set id of a doc, if provided, will be sent in with the next url param
    :param docs: a pre selected subset to select randomly from
    '''
    collection = get_doc_collection(did)
    if docs == None:
        docs = doc.objects.filter(collection=collection)

    # Get a random doc (if gets slow, change to get_random_doc
    doc = select_random_docs(docs)[0]

    # Ensure url returned is for doc
    if sid != None:
        return HttpResponseRedirect(reverse('annotate_doc',  kwargs={'rid': doc.id, 
                                                                        'sid': sid}))
    return HttpResponseRedirect(reverse('annotate_doc',  kwargs={'rid': doc.id}))

