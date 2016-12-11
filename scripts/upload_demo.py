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
from whatisit.apps.wordfish.models import (
    ReportCollection, 
    Report, 
    Annotation, 
    AllowedAnnotation
)

# Command to produce input data:
# singularity run -B $PWD:/data pefinder.img --reports /data/pefinder/data/ stanford_data.csv --delim ,  --output /data/stanford_pe.tsv --verbose
# from: https://github.com/vsoch/pe-predictive

input_file = "%s/scripts/stanford_pe.tsv" %(BASE_DIR)

if os.path.exists(input_file):
    data = pandas.read_csv(input_file,sep="\t")
    # For the user, get the first (not anon) one
    user = User.objects.all()[1]
    # First make a new collection
    collection,created = ReportCollection.objects.get_or_create(name="stanford-pe-predictive",
                                                                owner=user)
    if created == True:
        collection.save()
    # Add the creator as an annotator
    collection.annotators.add(user)
    collection.save()
    # For each data label, get possible annotations, create objects
    # Matches capital letters and _ followed by "_label"
    # ['PE_PRESENT_label', 'CERTAINTY_label', 'ACUITY_label', 'LOOKING_FOR_PE_label', 'QUALITY_label']
    label_columns = [x for x in data.columns if re.search('^[A-Z0-9|_]*_label$',x)]
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
    # If all labels are NULL, the user will (normally) need to add them manually, here we will
    # do it manually (and programatically :P)
    empty_groups = {"QUALITY_label":["DIAGNOSTIC","NON_DIAGNOSTIC"],
                    "LOOKING_FOR_PE_label":["PE_STUDY","NONPESTUDY"]}
    for eg_label, label_options in empty_groups.items():
        label_options = [x.replace(" ","_").lower() for x in label_options]
        # Save as AllowedAnnotation
        for label_option in label_options:
            allowed_annotation,created = AllowedAnnotation.objects.get_or_create(name=eg_label,
                                                                                 label=label_option)
            if created == True:
                allowed_annotation.save()
            allowed_annotations.append(allowed_annotation)
    # Add allowed annotations to the collection
    [collection.allowed_annotations.add(x) for x in allowed_annotations]
    collection.save()
    # Note: The annotations themselves will be stored in separate objects)
    labels = [a.name for a in AllowedAnnotation.objects.all()]
    labels = numpy.unique(labels).tolist()
    # Create a robot user to associate with the annotations
    robot = User.objects.create(username='pefinder') #password not provided here
    robot.save()
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
            # if the value isn't Null, add annotation to the report
            if not pandas.isnull(row[1][report_annotation]):
                value = row[1][report_annotation].replace(" ","_").lower()
                annotation_object = AllowedAnnotation.objects.get(name=report_annotation,
                                                                  label=value)
                annotation,created = Annotation.objects.get_or_create(annotator=robot,
                                                                      annotation=annotation_object)
                if created==True:
                    annotation.save()
                annotation.reports.add(new_report)
                annotation.save()


#Annotation.objects.count()
#7
#AllowedAnnotation.objects.count()
#11
#Report.objects.count()
#117816

else:
    print("Cannot find file %s.\n It is not included in the repo, did you get it from @vsoch?" %(input_file))
