from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.urlresolvers import reverse
from django.db import models

from whatisit.apps.wordfish.models import (
    ReportCollection,
    ReportSet
)

from whatisit.settings import MEDIA_ROOT

import collections
import operator
import os


#######################################################################################################
# Supporting Functions and Variables ##################################################################
#######################################################################################################


# Create a token for the user when the user is created (with oAuth2)
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


# Get path to where images are stored for teams
def get_image_path(instance, filename):
    team_folder = os.path.join(MEDIA_ROOT,'teams')
    if not os.path.exists(team_folder):
        os.mkdir(team_folder)
    return os.path.join('teams', filename)


REQUEST_CHOICES = (("PENDING","PENDING"),
                   ("APPROVED","APPROVED"),
                   ("DENIED","DENIED"))


STATUS_CHOICES = (("PASSED","PASSED"),
                  ("TESTING","TESTING"),
                  ("DENIED","DENIED"))


#######################################################################################################
# Membership and Credentials ##########################################################################
#######################################################################################################


class RequestMembership(models.Model):
    '''A request for membership is tied to a collection - a user is granted access if the owner grants him/her permission.
    '''
    requester = models.ForeignKey(User,related_name="sender")
    collection = models.ForeignKey(ReportCollection,related_name="requested_membership_collection")
    created_at = models.DateTimeField('date of request', auto_now_add=True)
    status = models.CharField(max_length=200, null=False, verbose_name="Status of request", default="PENDING",choices=REQUEST_CHOICES)
    
    def __str__(self):
        return "<%s:%s>" %(self.requester,self.collection.id)

    def __unicode__(self):
        return "<%s:%s>" %(self.requester,self.collection.id)

    def get_label(self):
        return "users"

    class Meta:
        app_label = 'users'

        # This prevents a single user from spamming multiple requests
        unique_together =  (("requester", "collection"),)


class Credential(models.Model):
    '''A Credential is used to determine if a particular user has tested successfully to annotation a report set. It has a default
    expiration time of 2 weeks, unless specified otherwise.
    '''
    user = models.ForeignKey(User,related_name="user_credential_for")
    report_set = models.ForeignKey(ReportSet,related_name="report_set_credential_for")
    created_at = models.DateTimeField('date of credential creation', auto_now_add=True)
    updated_at = models.DateTimeField('date of updated credential', null=True, blank=True) # Updated when the user tests
    status = models.CharField(max_length=200, null=False, verbose_name="Status of credential", default="TESTING",choices=STATUS_CHOICES)
    duration_weeks = models.CharField(max_length=100,null=False,default="2",verbose_name="Duration of credential, in weeks")
    
    def __str__(self):
        return "<%s:%s>" %(self.user,self.report_set.id)

    def __unicode__(self):
        return "<%s:%s>" %(self.user,self.report_set.id)

    def get_label(self):
        return "users"

    class Meta:
        app_label = 'users'

        # This prevents a single user from spamming multiple requests
        unique_together =  (("user", "report_set"),)


class TestingSession(models.Model):
    '''a testing session holds a user testing session
    that can be generated specific to a report set. The report set itself
    is stored in a request.session with the TestingSession id as lookup'''
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    report_set = models.ForeignKey(ReportSet)
    correct = models.PositiveIntegerField(blank=False,null=False,default=0)
    incorrect = models.PositiveIntegerField(blank=False,null=False,default=0)

    class Meta:
        unique_together =  (("user", "report_set"),)


#######################################################################################################
# Teams ###############################################################################################
#######################################################################################################


class Team(models.Model):
    '''A user team is a group of individuals that are annotating reports together. They can be reports across collections, or 
    institutions, however each user is only allowed to join one team.
    '''
    name = models.CharField(max_length=250, null=False, blank=False,verbose_name="Team Name")
    created_at = models.DateTimeField('date of creation', auto_now_add=True)
    updated_at = models.DateTimeField('date of last update', auto_now=True)
    team_image = models.ImageField(upload_to=get_image_path, blank=True, null=True)    
    metrics_updated_at = models.DateTimeField('date of last calculation of rank and annotations',blank=True,null=True)
    ranking = models.PositiveIntegerField(blank=True,null=True,
                                          verbose_name="team ranking based on total number of annotations, calculated once daily.")
    annotation_count = models.IntegerField(blank=False,null=False,
                                           verbose_name="team annotation count, calculated once daily.",
                                           default=0)
    members = models.ManyToManyField(User, 
                                     related_name="team_members",
                                     related_query_name="team_members", blank=True, 
                                     help_text="Members of the team. By default, creator is made member.")
                                     # would more ideally be implemented with User model, but this will work
                                     # we will constrain each user to joining one team on view side

    def __str__(self):
        return "<%s:%s>" %(self.id,self.name)

    def __unicode__(self):
        return "<%s:%s>" %(self.id,self.name)

    def get_absolute_url(self):
        return_cid = self.id
        return reverse('team_details', args=[str(return_cid)])

    def get_label(self):
        return "users"

    class Meta:
        app_label = 'users'

