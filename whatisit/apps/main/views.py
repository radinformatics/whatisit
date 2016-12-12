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
    return render(request,'main/404.html')

def handler500(request):
    return render(request,'main/500.html')
