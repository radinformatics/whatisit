#!/bin/python
# This script will upload the data from @mlungren's project, including basic reports and labels
# (see README.md for full instructions). In the long run we want a standard data format for importing.

# Labels stored with each report look like this: a label (key of dict) with options (list of values)
# {'historicity_label': ['new', 'mixed', 'old'], 'uncertainty_label': ['definitely negative', 'definitely positive', 'probably negative', 'Indeterminate', 'probably positive'], 'disease_state_label': ['definitely negative', 'definitely positive', 'probably negative', 'Indeterminate', 'probably positive'], 'quality_label': ['diagnostic', 'limited', 'non-diagnostic']}

import os
import re
import pandas
from whatisit.settings import BASE_DIR

from django.contrib.auth.models import User
from whatisit.apps.labelinator.models import ReportCollection, Report, Annotation

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

    uid = models.CharField(max_length=250, null=False, blank=False)
    text = models.CharField(max_length=5000, null=False, blank=False)
    #image = models.FileField(upload_to=get_upload_folder,null=True,blank=False)
    annotators = models.ManyToManyField(User,related_name="report_annotators",related_query_name="annotator", blank=True,help_text="users that have annotated the report.",verbose_name="Annotators")
    labels = JSONField()
    collection = models.ForeignKey(ReportCollection,null=False,blank=False)
    tags = TaggableManager()

    # For each data label, get possible annotations
    label_columns = [x for x in data.columns if re.search('_label$',x)]
    labels = dict()
    for label_column in label_columns:
        label_options = data[label_column][data[label_column].isnull()==False].unique().tolist()
        # We only want lowercase, spaces converted to "_"
        label_options = [x.replace(" ","_").lower() for x in label_options]
        labels[label_column] = label_options

    # Note: The annotations themselves will be stored in separate objects)

    # Now upload reports to it!
    for row in data.iterrows():
        print("Parsing %s of %s" %(row[0],data.shape[0]))
        # Which labels do we have?
        report_annotations = [x for x in row[1].index if x in labels]
        # For each label, create an annotation (for annotator user) if it isn't null
        annotations = []
        for report_annotation in report_annotations:
            if not pandas.isnull(row[1][report_annotation]):
                value = row[1][report_annotation].replace(" ","_").lower()
                annotation,created = Annotation.objects.get_or_create(annotator=user,
                                                                      label=report_annotation,
                                                                      annotation=value)
                if created==True:
                    annotation.save()
                annotations.append(annotation)
        # Now add the report with the annotations
        report_text = row[1].report_text
        report_id = row[1].report_id
        new_report, created = Report.objects.get_or_create(report_id=report_id,
                                                           report_text=report_text,
                                                           collection=collection,
                                                           labels=labels)    
        if created == True:
            [new_report.annotations.add(x) for x in annotations]   
            new_report.save()

else:
    print("Cannot find file %s.\n It is not included in the repo, did you get it from @vsoch?" %(input_file))
