#!/bin/python
# This script will upload the data from @mlungren's project, including basic reports and labels
# (see README.md for full instructions). In the long run we want a standard data format for importing.

# AllowedAnnotation objects store a label name and allowed value, and an Annotation combines one of these objects
# with a list of reports and a user, for easy query/filter

import os
import re
import pandas
import numpy
from whatisit.settings import BASE_DIR

from django.contrib.auth.models import User
from whatisit.apps.labelinator.models import ReportCollection, Report, Annotation, AllowedAnnotation

input_file = "%s/scripts/data.tsv" %(BASE_DIR)

if os.path.exists(input_file):
    data = pandas.read_csv(input_file,sep="\t")
    # For the user, get the first (not anon) one
    user = User.objects.all()[1]
    # First make a new collection
    collection,created = ReportCollection.objects.get_or_create(name="stanford-pe-predictive",
                                                                owner=user)
    if created == True:
        collection.save()
    # For each data label, get possible annotations, create objects
    label_columns = [x for x in data.columns if re.search('_label$',x)]
    allowed_annotations = []
    for label_column in label_columns:
        label_options = data[label_column][data[label_column].isnull()==False].unique().tolist()
        # We only want lowercase, spaces converted to "_"
        label_options = [x.replace(" ","_").lower() for x in label_options]
        # Save as AllowedAnnotation
        for label_option in label_options:
            allowed_annotation,created = AllowedAnnotation.objects.get_or_create(name=label_column,
                                                                                 label=label_option)
            if created == True:
                allowed_annotation.save()
                allowed_annotations.append(allowed_annotation)
    # Note: The annotations themselves will be stored in separate objects)
    labels = [a.name for a in AllowedAnnotation.objects.all()]
    labels = numpy.unique(labels).tolist()

    # Now upload reports to it!
    for row in data.iterrows():
        print("Parsing %s of %s" %(row[0],data.shape[0]))
        # Which labels do we have?
        report_annotations = [x for x in row[1].index if x in labels]
        # Now add the report with the annotations, and allowed annotations
        report_text = row[1].report_text
        report_id = row[1].report_id
        new_report, created = Report.objects.get_or_create(report_id=report_id,
                                                           report_text=report_text,
                                                           collection=collection)
        if created == True:
            new_report.save()
        # For each label, create an annotation (for annotator user) if it isn't null
        for report_annotation in report_annotations:
            if not pandas.isnull(row[1][report_annotation]):
                value = row[1][report_annotation].replace(" ","_").lower()
                annotation_object = AllowedAnnotation.objects.get(name=report_annotation,
                                                                  label=value)
                annotation,created = Annotation.objects.get_or_create(annotator=user,
                                                                      annotation=annotation_object)
                if created==True:
                    annotation.save()
                annotation.reports.add(new_report)
                annotation.save()


#Annotation.objects.count()
#16
#AllowedAnnotation.objects.count()
#16
#Report.objects.count()
#117816

else:
    print("Cannot find file %s.\n It is not included in the repo, did you get it from @vsoch?" %(input_file))
