from guardian.shortcuts import assign_perm, get_users_with_perms, remove_perm
from polymorphic.models import PolymorphicModel
from taggit.managers import TaggableManager

from whatisit.apps.wordfish.storage import ImageStorage
from whatisit.settings import MEDIA_ROOT

from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.urlresolvers import reverse
from django.db.models.signals import m2m_changed
from django.db.models import Q, DO_NOTHING
from django.db import models

import collections
import operator
import os

#######################################################################################################
# Supporting Functions and Variables ##################################################################
#######################################################################################################

def get_upload_folder(instance,filename):
    '''get_upload_folder will return the folder for an image associated with the ImageSet id.
    instance: the Image instance to upload to the ImageCollection
    filename: the filename of the image
    '''
    collection_id = instance.collection.id
    # This is relative to MEDIA_ROOT
    return os.path.join(str(collection_id), filename)



PRIVACY_CHOICES = ((False, 'Public (The collection will be accessible by anyone and all the data in it will be distributed under CC0 license)'),
                   (True, 'Private (The collection will be not listed. It will be possible to share it with others at a private URL.)'))


#######################################################################################################
# Allowed Annotations #################################################################################
#######################################################################################################

class AllowedAnnotation(models.Model):
    '''An allowed annotation is key/list of labels lookup to find allowable annotations
    '''
    
    # The annotation is what the user labeled the report with
    name = models.CharField(max_length=250, null=False, blank=False,help_text="term the user labeled the report with")
    # The label is the what "field/thing" the annotation is describing
    label = models.CharField(max_length=250, null=False, blank=False,help_text="label allowed for the term")

    
    def __str__(self):
        return "<%s>" %(self.name)

    def __unicode__(self):
        return "<%s>" %(self.name)

    def get_label(self):
        return "wordfish"

    class Meta:
        ordering = ['name']
        app_label = 'wordfish'

        # A specific annotator can only give one label for some annotation label
        unique_together =  (("name", "label"),)




#######################################################################################################
# Reports #############################################################################################
#######################################################################################################

class ReportCollection(models.Model):
    '''A report collection is a grouping of reports owned by one or more users
    '''

    # Report Collection Descriptors
    name = models.CharField(max_length=200, null=False, verbose_name="Name of collection")
    description = models.TextField(blank=True, null=True)
    add_date = models.DateTimeField('date published', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    allowed_annotations = models.ManyToManyField(AllowedAnnotation,related_name="reports_allowed_annotation",related_query_name="annotations_allowed_collection", blank=True,verbose_name="Annotations allowed for Report Collection")
    markup = models.CharField(max_length=1000, null=True, blank=True, 
                                  default="no,evidence,diagnosis,rx,positive,negative",
                                  verbose_name="Default tags to highlight.")
    
    # Users
    owner = models.ForeignKey(User)
    contributors = models.ManyToManyField(User,related_name="container_collection_contributors",related_query_name="contributor", blank=True,help_text="Select other users to add as contributes to the collection.",verbose_name="Contributors")
    annotators = models.ManyToManyField(User,related_name="container_collection_annotators",related_query_name="collection_annotator", blank=True,help_text="Other users given permission to annotate sets for the collection.",verbose_name="Collection Annotators")

    # Privacy
    private = models.BooleanField(choices=PRIVACY_CHOICES, default=False,verbose_name="Is the collection private?")
    private_token = models.CharField(max_length=8,blank=True,null=True,
                                     unique=True,db_index=True, default=None)

    def get_absolute_url(self):
        return_cid = self.id
        return reverse('report_collection_details', args=[str(return_cid)])

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def get_label(self):
        return "report_collection"

    def save(self, *args, **kwargs):
        super(ReportCollection, self).save(*args, **kwargs)
        assign_perm('del_report_collection', self.owner, self)
        assign_perm('edit_report_collection', self.owner, self)

    class Meta:
        ordering = ["name"]
        app_label = 'wordfish'
        permissions = (
            ('del_report_collection', 'Delete report collection'),
            ('edit_report_collection', 'Edit report collection'),
            ('annotate_report_collection', 'Annotate report collection')
        )



class Report(models.Model):
    '''A report is a text string associated with a report collection and
    one or more labels.
    '''
    report_id = models.CharField(max_length=250, null=False, blank=False)
    report_text = models.CharField(max_length=50000, null=False, blank=False)
    #image = models.FileField(upload_to=get_upload_folder,null=True,blank=False)
    collection = models.ForeignKey(ReportCollection,null=False,blank=False)
    tags = TaggableManager()
    
    def __str__(self):
        return "<Report:%s|%s>" %(self.collection,self.report_id)

    def __unicode__(self):
        return "<Report:%s|%s>" %(self.collection,self.report_id)
 
    def get_label(self):
        return "report"

    class Meta:
        ordering = ['report_id']
        app_label = 'wordfish'
 
        # Container names in a collection must be unique
        unique_together =  (("report_id", "collection"),)

    # Get the url for a report collection
    def get_absolute_url(self):
        return_cid = self.id
        return reverse('report_details', args=[str(return_cid)])


class ReportSet(models.Model):
    '''A report set is a particular subset of reports with permissions for users to annotate
    '''
    name = models.CharField(max_length=250, null=False, blank=False)
    gold_standard = models.ForeignKey(User,related_name="gold_standard_annotator",
                                     related_query_name="gold_standard_annotator",
                                     blank=False,
                                     help_text="The annotations of this user will be used to score tests.",
                                     verbose_name="Gold Standard Annotator, whose annotations will be standard for testing.")

    add_date = models.DateTimeField('date published', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    annotators = models.ManyToManyField(User,related_name="users_allowed_annotation",
                                     related_query_name="users_allowed_annotation", 
                                     blank=True,
                                     verbose_name="Users allowed to annotate report set.")    

    collection = models.ForeignKey(ReportCollection)
    number_tests = models.PositiveIntegerField(blank=False,null=False,
                                     verbose_name="total number of randomly selected high confidence reports to test", 
                                     default=20)

    passing_tests = models.PositiveIntegerField(blank=False,null=False,
                                     verbose_name="number of correct responses at which a user is given credit",
                                     default=15)

    testing_annotations = models.ManyToManyField(AllowedAnnotation,  
                                     related_name="allowed_annotations_testing",
                                     related_query_name="allowed_annotations_testing", blank=True, 
                                     help_text="Annotations to test the user with.",
                                     verbose_name="Select all annotations and labels that must be chosen (when applicable) to give the user a correct point. This means that choosing two labels can give a user two points for one report. Choosing one version of a label (eg, positive X but not negative X) will mean that both negative and positive will be included when testing X.")

    reports = models.ManyToManyField(Report,
                                     related_name="reports_in_set",
                                     related_query_name="reports_in_set", 
                                     blank=True,
                                     verbose_name="Reports in report set.")  

    def __str__(self):
        return "%s-%s" %(self.id,self.collection)

    def __unicode__(self):
        return "%s-%s" %(self.id,self.collection)

    def get_label(self):
        return "report_set"

    def save(self, *args, **kwargs):
        super(ReportSet, self).save(*args, **kwargs)
        assign_perm('del_report_set', self.collection.owner, self)
        assign_perm('edit_report_set', self.collection.owner, self)

    class Meta:
        app_label = 'wordfish'
        permissions = (
            ('del_report_set', 'Delete report set'),
            ('edit_report_set', 'Edit report set')
        )


#######################################################################################################
# Annotations #########################################################################################
#######################################################################################################

class Annotation(models.Model):
    '''An annotation is a report is a text string associated with a report collection and
    one or more labels.
    '''
    # Who did the annotation? This is the annotator?
    annotator = models.ForeignKey(User,related_name="annotator",related_query_name="annotator", blank=False,help_text="user that created the annotation.",verbose_name="Annotator")
    # The annotation is what the user labeled the report with
    annotation = models.ForeignKey(AllowedAnnotation,blank=False,help_text="the name,labels allowed for this particular annotation")
    reports = models.ManyToManyField(Report,related_name="reports_annotated",related_query_name="reports_annotated", blank=True,verbose_name="Reports Annotated")

    tags = TaggableManager()
    
    def __str__(self):
        return "<annotation:%s>" %(self.id)

    def __unicode__(self):
        return "<annotation:%s>" %(self.id)

    def get_label(self):
        return "wordfish"

    class Meta:
        ordering = ['annotator','id']
        app_label = 'wordfish'
 
        # A specific annotator can only give one label for some annotation label
        unique_together =  (("id", "annotation","annotator"),)


def contributors_changed(sender, instance, action, **kwargs):
    if action in ["post_remove", "post_add", "post_clear"]:
        current_contributors = set([user.pk for user in get_users_with_perms(instance)])
        new_contributors = set([user.pk for user in [instance.owner, ] + list(instance.contributors.all())])

        for contributor in list(new_contributors - current_contributors):
            contributor = User.objects.get(pk=contributor)
            assign_perm('annotate_report_collection', contributor, instance)

        for contributor in (current_contributors - new_contributors):
            contributor = User.objects.get(pk=contributor)
            remove_perm('annotate_report_collection', contributor, instance)

def annotators_changed(sender, instance, action, **kwargs):
    if action in ["post_remove", "post_add", "post_clear"]:
        current_annotators = set([user.pk for user in get_users_with_perms(instance)])
        new_annotators = set([user.pk for user in [instance.owner, ] + list(instance.annotators.all())])

        for contributor in list(new_annotators - current_annotators):
            contributor = User.objects.get(pk=contributor)
            assign_perm('edit_report_collection', contributor, instance)

        for contributor in (current_annotators - new_annotators):
            contributor = User.objects.get(pk=contributor)
            remove_perm('edit_report_collection', contributor, instance)


m2m_changed.connect(contributors_changed, sender=ReportCollection.contributors.through)
m2m_changed.connect(annotators_changed, sender=ReportCollection.annotators.through)
