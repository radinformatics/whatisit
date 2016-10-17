from django.template import RequestContext
from django.shortcuts import render, render_to_response
import hashlib

def index_view(request):
    context = {}
    return render(request, 'main/index.html', context)

def about_view(request):
    context = {'active':'home'}
    return render(request, 'main/about.html', context)

# Error Pages ##################################################################

def handler404(request):
    response = render_to_response('main/404.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 404
    return response

def handler500(request):
    response = render_to_response('main/500.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 500
    return response
