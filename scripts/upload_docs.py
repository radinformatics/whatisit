#!/bin/python
# This script will upload the data for dockerfiles, for use with the tagging view

import os
import re
import pandas
import pickle
import numpy
from whatisit.settings import BASE_DIR

from django.contrib.auth.models import User
from whatisit.apps.tagtrout.models import (
    DocsCollection, 
    Doc
)

input_file = "%s/scripts/dockerfiles.pkl" %(BASE_DIR)

if os.path.exists(input_file):
    data = pickle.load(open(input_file,'rb'))
    # For the user, get the first (not anon) one
    user = User.objects.get(id=2)
    # First make a new collection
    collection_name = "Dockerfiles"
    collection,created = DocsCollection.objects.get_or_create(name=collection_name,
                                                              owner=user)
    if created == True:
        collection.save()
    # Add the creator as an annotator
    collection.contributors.add(user)
    collection.save()

    # Now upload docs to it!
    for name,text in data.items():
        print("Parsing %s" %(name))
        new_doc, created = Doc.objects.get_or_create(doc_id=name,
                                                      doc_text=text,
                                                      collection=collection)
        if created == True:
            new_doc.save()
else:
    print("Cannot find file %s.\n It is not included in the repo, did you get it from @vsoch?" %(input_file))
