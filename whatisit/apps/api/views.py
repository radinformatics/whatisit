from django.http import (
    Http404, 
    JsonResponse, 
    HttpResponse
)

from django.template import RequestContext
from django.shortcuts import (
    render, 
    render_to_response
)

import hashlib

from whatisit.settings import API_VERSION as APIVERSION
from whatisit.apps.wordfish.models import (
    Report, 
    ReportCollection,
    ReportSet
)

from whatisit.apps.wordfish.utils import (
    get_annotation_counts,
    get_report_collection,
    get_report_set
)

from rest_framework import (
    viewsets, 
    generics
)

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from whatisit.apps.api.serializers import (
    ReportSerializer, 
    ReportSetSerializer,
    ReportCollectionSerializer
)

from whatisit.apps.api.utils import chooseJsonResponse

from django.contrib.auth.models import User



#########################################################################
# Auth
# get user tokens!
#########################################################################

def get_token(request,json_response=True):
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
    all reports to be viewed (currently not exposed)
    '''
    queryset = Report.objects.all().order_by('report_id')
    serializer_class = ReportSerializer


class ReportCollectionViewSet(viewsets.ReadOnlyModelViewSet):
    '''ReportCollectionViewSet is an API endpoint that allows 
    all report collections to br viewed
    '''
    queryset = ReportCollection.objects.all()
    serializer_class = ReportCollectionSerializer


class ReportSetViewSet(viewsets.ReadOnlyModelViewSet):
    '''ReportSetViewSet is an API endpoint that allows 
       all report sets to be viewed.
    '''
    queryset = ReportSet.objects.all()
    serializer_class = ReportSetSerializer


#########################################################################
# GET
# requests for information about reports and collections
#########################################################################


class ReportGet(APIView):
    """Retrieve a single report based on report_id
    """
    def get_object(self, report_id):
        report = get_report(report_id)

    def get(self, request, report_id):
        report = self.get_object(report_id)
        serializer = SingleReportSerializer(report)
        return Response(serializer.data)


class ReportSetGet(APIView):
    """Retrieve an annotation set's annotations
    """
    def get_object(self, set_id):
        report_set = get_report_set(set_id)

    def get(self, request, set_id):
        container = self.get_object(set_id)

        serializer = SingleReportSetSerializer(report_set)
        return Response(serializer.data)



#########################################################################
# JSON for views
#########################################################################


@api_view(['GET'])
def get_annotation_counts(request,cid):
    '''get_annotation_counts serves the get_annotation_counts function
    from wordfish.utils as an API endpoint
    :param cid: should be the collection id
    '''
    collection = get_report_collection(cid)
    counts = get_annotation_counts(collection)
    return JsonResponse({"counts":counts,
                         "collection":collection.id})


