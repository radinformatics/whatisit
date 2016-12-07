from django.http import Http404, JsonResponse, HttpResponse
from django.template import RequestContext
from django.shortcuts import render, render_to_response
import hashlib

from whatisit.settings import API_VERSION as APIVERSION
from whatisit.apps.wordfish.models import Report, ReportCollection

from rest_framework import viewsets, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from whatisit.apps.api.serializers import ReportSerializer, ReportCollectionSerializer
from whatisit.apps.api.utils import chooseJsonResponse

from django.contrib.auth.models import User

#########################################################################
# Auth
# get user tokens!
#########################################################################

def getToken(request,json_response=True):
    '''getToken is used to authenticate a user.
    :param json_response: if True, seld JsonResponse. Otherwise, json
    '''
    # On error, make sure user knows that...
    message = '''/api/token is only available when being called 
                 from within a browser'''

    if request.user != None and request.user.is_anonymous() == False:
        try:
            token = request.user.auth_token
        except User.DoesNotExist:

            # Tell the user the error is not found
            response = {'error': 'User not found.','message':message}
            return chooseJsonResponse(response,json_response,status=404)
 
        response = {"token":token.key}
        return chooseJsonResponse(response,json_response)

    else:
        response = {'error': 'User not authenticated.','message': message }
        return chooseJsonResponse(response,json_response,status=401)


#########################################################################
# GET
# requests for information about reports and collections
#########################################################################

def api_view(request,api_version=None):
    if api_version == None:
        api_version = APIVERSION

    # In future, we can then return different versions  of docs for api
    context = {"api_version":api_version}
    return render(request, 'routes/api.html', context)

class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    '''ReportViewSet is an API endpoint that allows 
       all containers to be viewed.
    '''
    queryset = Report.objects.all().order_by('report_id')
    serializer_class = ReportSerializer


class ReportCollectionViewSet(viewsets.ReadOnlyModelViewSet):
    '''ReportCollectionViewSet is an API endpoint that allows 
       all container collections to be viewed.
    '''
    queryset = ReportCollection.objects.all()
    serializer_class = ReportCollectionSerializer
