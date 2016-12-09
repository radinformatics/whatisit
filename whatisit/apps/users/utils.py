from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from whatisit.apps.wordfish.models import (
    ReportCollection,
    ReportSet
)
from whatisit.apps.users.models import (
    Credential,
    RequestPermission
)
import collections
import operator
import os


def get_has_credentials(report_set,return_users=True):
    '''get a list of users that have credentials (either status is TESTING or PASSED) for
    a report set.
    :param return_users: return list of users (not credentials) default is True
    '''
    has_credential = Credential.objects.filter(report_set=report_set,
                                               status__in=["TESTING","PASSED"])
    if return_users == True:
        has_credential = [x.user for x in has_credential]
    return has_credential


def get_credential_contenders(report_set,return_users=True):
    '''get a list of users that have permission to annotate a collection, but have
    not had a credential created.
    :param return_users: return list of users (not credentials) default is True
    '''
    # Get list of allowed annotators for set, not in set (to add)
    all_annotators = RequestMembership.objects.filter(collection=report_set.collection)
    all_annotators = [x.requester for x in all_annotators]
    has_credential = get_has_credential(report_set)
    contenders = [user for user in all_annotators if user not in has_credentials]
    return contenders


REQUEST_CHOICES = (("PENDING","PENDING"),
                   ("APPROVED","APPROVED"),
                   ("DENIED","DENIED"))


STATUS_CHOICES = (("PASSED","PASSED"),
                  ("TESTING","TESTING"),
                  ("DENIED","DENIED"))


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
    updated_at = models.DateTimeField('date of updated credential', auto_now=True)
    status = models.CharField(max_length=200, null=False, verbose_name="Status of credential", default="TESTING",choices=STATUS_CHOICES)
    duration_weeks = models.CharField(max_length=100,null=False,default="2",verbose_name="Duration of credential, in weeks")
    
    def __str__(self):
        return "<%s:%s>" %(self.user,self.report_set.id)

    def __unicode__(self):y
        return "<%s:%s>" %(self.user,self.report_set.id)

    def get_label(self):
        return "users"

    class Meta:
        app_label = 'users'

        # This prevents a single user from spamming multiple requests
        unique_together =  (("user", "report_set"),)
