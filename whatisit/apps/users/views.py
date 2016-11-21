from django.shortcuts import render_to_response, redirect, render
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from whatisit.apps.api.views import getToken
from django.template.context import RequestContext

import logging
import os
import pickle

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect


def login(request):
    # context = RequestContext(request, {
    #     'request': request, 'user': request.user})
    # return render_to_response('login.html', context_instance=context)
    return render(request, 'social/login.html')


@login_required(login_url='/')
def home(request):
    return render_to_response('social/home.html')

@login_required
def token(request):
    '''getToken retrieves the user's token, and returns a page with it
    for the user to use to authenticate with the API
    '''
    token = getToken(request,json_response=False)
    context = RequestContext(request, {'request': request, 
                                       'user': request.user,
                                       'token': token['token'] })
    return render_to_response("users/token.html", context_instance=context)

def logout(request):
    auth_logout(request)
    return redirect('/')


# Python social auth extensions

def redirect_if_no_refresh_token(backend, response, social, *args, **kwargs):
    '''http://python-social-auth.readthedocs.io/en/latest/use_cases.html#re-prompt-google-oauth2-users-to-refresh-the-refresh-token
    '''
    if backend.name == 'google-oauth2' and social and response.get('refresh_token') is None and social.extra_data.get('refresh_token') is None:
        return redirect('/login/google-oauth2?approval_prompt=force')

## A User should not be allowed to associate a Github (or other) account with a different
# gmail, etc.

def social_user(backend, uid, user=None, *args, **kwargs):
    '''OVERRIDED: It will give the user an error message if the
    account is already associated with a username.'''
    provider = backend.name
    social = backend.strategy.storage.user.get_social_auth(provider, uid)
    if social:
        if user and social.user != user:
            msg = 'This {0} account is already in use.'.format(provider)
            return login(request=backend.strategy.request,
                         message=msg)
            #raise AuthAlreadyAssociated(backend, msg)
        elif not user:
            user = social.user

    return {'social': social,
            'user': user,
            'is_new': user is None,
            'new_association': social is None}
