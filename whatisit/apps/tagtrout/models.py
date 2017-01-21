from guardian.shortcuts import assign_perm, get_users_with_perms, remove_perm
from polymorphic.models import PolymorphicModel
from taggit.managers import TaggableManager

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
# Reports #############################################################################################
#######################################################################################################

class DocsCollection(models.Model):
    '''A report collection is a grouping of reports owned by one or more users
    '''

    # Report Collection Descriptors
    name = models.CharField(max_length=200, null=False, verbose_name="Name of collection")
    description = models.TextField(blank=True, null=True)
    add_date = models.DateTimeField('date published', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    
    # Users
    owner = models.ForeignKey(User)
    contributors = models.ManyToManyField(User,related_name="container_collection_contributors",related_query_name="contributor", blank=True,help_text="Select other users to add as contributes to the collection.",verbose_name="Contributors")

    def get_absolute_url(self):
        return_cid = self.id
        return reverse('docs_collection_details', args=[str(return_cid)])

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def get_label(self):
        return "docs_collection"

    def save(self, *args, **kwargs):
        super(ReportCollection, self).save(*args, **kwargs)
        assign_perm('del_docs_collection', self.owner, self)
        assign_perm('edit_docs_collection', self.owner, self)

    class Meta:
        ordering = ["name"]
        app_label = 'tagtrout'
        permissions = (
            ('del_docs_collection', 'Delete docs collection'),
            ('edit_docs_collection', 'Edit docs collection'),
        )



class Doc(models.Model):
    '''A doc is something that you want to tag.
    '''
    doc_id = models.CharField(max_length=250, null=False, blank=False)
    doc_text = models.CharField(max_length=50000, null=False, blank=False)
    #image = models.FileField(upload_to=get_upload_folder,null=True,blank=False)
    collection = models.ForeignKey(DocCollection,null=False,blank=False)
    tags = TaggableManager()
    
    def __str__(self):
        return "%s|%s" %(self.collection,self.doc_id)

    def __unicode__(self):
        return "%s|%s" %(self.collection,self.doc_id)
 
    def get_label(self):
        return "report"

    class Meta:
        ordering = ['doc_id']
        app_label = 'tagtrout'
 
        # Container names in a collection must be unique
        unique_together =  (("doc_id", "collection"),)

    # Get the url for a report collection
    def get_absolute_url(self):
        return_cid = self.id
        return reverse('doc_details', args=[str(return_cid)])


def contributors_changed(sender, instance, action, **kwargs):
    if action in ["post_remove", "post_add", "post_clear"]:
        current_contributors = set([user.pk for user in get_users_with_perms(instance)])
        new_contributors = set([user.pk for user in [instance.owner, ] + list(instance.contributors.all())])

        for contributor in list(new_contributors - current_contributors):
            contributor = User.objects.get(pk=contributor)
            assign_perm('edit_docs_collection', contributor, instance)

        for contributor in (current_contributors - new_contributors):
            contributor = User.objects.get(pk=contributor)
            remove_perm('edit_docs_collection', contributor, instance)


m2m_changed.connect(contributors_changed, sender=DocsCollection.contributors.through)
