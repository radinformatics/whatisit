from django.shortcuts import render_to_response, redirect, render
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from whatisit.apps.api.views import getToken
from django.template.context import RequestContext


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
