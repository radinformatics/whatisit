from django.shortcuts import render_to_response, redirect, render
from django.contrib import messages
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

from whatisit.apps.users.forms import TeamForm
from whatisit.apps.users.models import Team
from whatisit.apps.users.utils import (
    get_team
    has_team_edit_permission,
    remove_user_teams
)


##################################################################################
# AUTHENTICATION VIEWS ###########################################################
##################################################################################

def login(request):
    context = {'request': request, 'user': request.user}
    context = RequestContext(request,context)
    return render_to_response('social/login.html', context_instance=context)
    #return render(request, 'social/login.html')


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
    '''log out of the social authentication backend'''
    auth_logout(request)
    return redirect('/')


##################################################################################
# TEAM VIEWS #####################################################################
##################################################################################


@login_required
def edit_team(request, tid=None):
    '''edit_team is the view to edit an existing team, or create a new team.
    :parma tid: the team id to edit or create. If none, indicates a new team
    '''
    if tid:
        team = get_team(request,tid)
    else:
        team = Team()

    # Only the owner is allowed to edit a team
    if has_team_edit_permission(request,team):

        if request.method == "POST":
            form = TeamForm(request.POST,instance=team)
            if form.is_valid():
                team = form.save(commit=False)
                team.save()
                team.members.add(request.user)
                team.save()
                return HttpResponseRedirect(team.get_absolute_url())
        else:
            form = TeamForm(instance=team)

        edit_permission = has_team_edit_permission(request,team)
        context = {"form": form,
                   "edit_permission": edit_permission}

        return render(request, "teams/edit_team.html", context)

    # If user makes it down here, does not have permission
    messages.info(request, "You don't have permission to edit this team")
    return redirect("teams")


def view_teams(request):
    '''view all teams (log in not required)
    :parma tid: the team id to edit or create. If none, indicates a new team
    '''
    teams = Team.objects.all()
    #TODO here need to sort by annotations
    #TODO also need to get user's team, if authetnicated
    context = {"teams": teams}
    return render(request, "teams/all_teams.html", context)


@login_required
def view_team(request, tid):
    '''view the details about a team
    :parma tid: the team id to edit or create. If none, indicates a new team
    '''
    team = get_team(request,tid)

    # Only the owner is allowed to edit a team
    edit_permission = has_team_edit_permission(request,team)

    context = {"team": team,
               "edit_permission":edit_permission}
    return render(request, "teams/team_details.html", context)


@login_required
def join_team(request, tid):
    '''add a user to a new team, and remove from previous team
    :parma tid: the team id to edit or create. If none, indicates a new team
    '''
    team = get_team(request,tid)
    user = request.user

    # Get the user's current team, and remove
    users_team = Team.objects.filter(members__contains=user)
    removed_team = remove_user_teams(remove_teams=users_team,
                                     user=user)

    # If the user was removed, tell him/her
    if removed_team != None:
        messages.info(request,"You have been removed from team %s" %(removed_team))

    # Add the user to the team
    if user not in team.members:
        team.members.add(user)
        team.save()
        messages.info(request,"%s has been successfully added to!" %(user.username,team.name))
    else:
        messages.info(request,"You are already a member of %s!" %(team.name))

    edit_permission = has_team_edit_permission(request,team)
    context = {"team": team,
               "edit_permission":edit_permission}
    return render(request, "teams/team_details.html", context)



# Python social auth extensions

def redirect_if_no_refresh_token(backend, response, social, *args, **kwargs):
    '''http://python-social-auth.readthedocs.io/en/latest/use_cases.html
       #re-prompt-google-oauth2-users-to-refresh-the-refresh-token
    '''
    if backend.name == 'google-oauth2' and social and response.get('refresh_token') is None and social.extra_data.get('refresh_token') is None:
        return redirect('/login/google-oauth2?approval_prompt=force')


# A User should not be allowed to associate a Github (or other) account with a different
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
