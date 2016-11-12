from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.urlresolvers import reverse
from django.db import models

from whatisit.apps.labelinator.models import ReportCollection

import collections
import operator
import os


# Create a token for the user when the user is created (with oAuth2)
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


REQUEST_CHOICES = (("PENDING","PENDING"),
                   ("APPROVED","APPROVED"),
                   ("DENIED","DENIED"))

class RequestMembership(models.Model):
    requester = models.ForeignKey(User,related_name="sender")
    collection = models.ForeignKey(ReportCollection,related_name="requested collection to have contributor status")
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
