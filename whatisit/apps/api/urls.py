from django.views.generic.base import TemplateView
from django.conf.urls import url, include

from rest_framework import routers
from rest_framework.authtoken import views as rest_views
from rest_framework_swagger.views import get_swagger_view

import whatisit.apps.api.views as api_views
from whatisit.settings import API_VERSION

router = routers.DefaultRouter()
router.register(r'^reports', api_views.ReportViewSet)
router.register(r'^sets', api_views.ReportSetViewSet)
router.register(r'^collections', api_views.ReportCollectionViewSet)

swagger_view = get_swagger_view(title='WordFish API',url='')

urlpatterns = [

    # Wire up our API using automatic URL routing.
    url(r'^$', swagger_view),
    url(r'^', include(router.urls)),
    url(r'^token/', api_views.get_token), # user token obtained in browser session
    url(r'^api-token-auth/', rest_views.obtain_auth_token), # user token obtained from command line
    # returns a JSON response when valid username and password fields are POSTed to the view using form data or JSON
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    # Always have default API view return current version
    url(r'^docs$', api_views.api_view, name="api"),

    # Custom API views for single reports, report_sets
    url(r'^report/(?P<report_id>.+?)$', api_views.ReportGet.as_view()),
    url(r'^collections/set/(?P<set_id>.+?)/annotations$', api_views.set_annotations.as_view()),

    # JSON CALLS FOR VIEWS
    url(r'^collection/(?P<cid>.+?)/counts$', api_views.get_annotation_counts), # user token obtained from command line
]
