from django.http import Http404, HttpResponse, JsonResponse

from django.contrib.auth.models import User
from rest_framework import authentication, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.decorators import parser_classes, authentication_classes, permission_classes
from rest_framework.parsers import JSONParser, FileUploadParser
from rest_framework.response import Response

from whatisit.apps.labelinator.models import Report, ReportCollection

@api_view(['POST'])
@parser_classes((JSONParser,))
def SpecUpload(request, format=None):
    """
    A view that can accept POST requests with JSON content.
    The JSON content is the recently uploaded spec.
    NOT WRITTEN YET
    """
    return Response({'received data': request.data})


class PushImage(APIView):
    parser_classes = (FileUploadParser,)
    queryset = Report.objects.none()  # Required for DjangoModelPermissions
    
    def put(self, request, collection, name, format=None):
        targz = request.data['file']

        # Does the user have permission to add to the collection?
        # STOPPED HERE - need to parse response and find the token!!
        #request.META["token"]

        # Is the file the correct name and extension?
        if targz == "Singularity.img.zip":
            
            with open(filename, 'wb+') as temp_file:
                for chunk in my_file.chunks():
                    temp_file.write(chunk)
        # ...
        # do some stuff with uploaded file
        # ...
        return Response(status=204)
