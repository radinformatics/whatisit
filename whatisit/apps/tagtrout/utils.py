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
from whatisit.apps.tagtrout.models import (
    Doc,
    DocsCollection
)

from whatisit.settings import MEDIA_ROOT
from random import randint
from numpy.random import shuffle
import numpy
import operator
import pandas
import shutil
import os
import re


#### GETS #############################################################

def get_doc(did):
    '''get a single doc, or return 404'''
    keyargs = {'id':did}
    try:
        doc = Doc.objects.get(**keyargs)
    except Doc.DoesNotExist:
        raise Http404
    else:
        return doc


def get_docs_collection(did):
    '''get a single collection, or return 404'''
    keyargs = {'id':did}
    try:
        collection = DocsCollection.objects.get(**keyargs)
    except DocsCollection.DoesNotExist:
        raise Http404
    else:
        return collection


def get_collection_users(collection):
    '''get_collection_users will return a list of all owners and contributors for
    a collection
    :param collection: the collection object to use
    '''
    contributors = collection.contributors.all()
    owner = collection.owner
    return list(chain(contributors,[owner]))


###########################################################################################
## SELECTION ALGORITHMS
###########################################################################################

def select_random_docs(docs,N=1):
    '''select random docs will select N docs from a provided set.
    '''
    docs = list(docs)
    shuffle(docs)
    # If enough docs are provided, select subset
    if len(docs) >= N:
        docs = docs[0:N]
    return docs


def select_random_doc(docs):
    '''select random doc will return one random doc
    :NOTE this function was buggy when used with doc_set,
    select_random_docs is being used in favor (needs testing)
    '''
    did = None
    while did == None:
        count = docs.aggregate(count=Count('id'))['count']
        did = randint(0, count - 1)
        try:
            doc = Doc.objects.get(id=did)
        except:
            did = None
    return doc
