from django.views.generic.base import TemplateView
from django.conf.urls import url, include

from rest_framework import routers
from rest_framework.authtoken import views as rest_views

import whatisit.apps.api.views as api_views
from whatisit.settings import API_VERSION

router = routers.DefaultRouter()
router.register(r'^reports', api_views.ReportViewSet)
router.register(r'^collections', api_views.ReportCollectionViewSet)


urlpatterns = [

    # Wire up our API using automatic URL routing.
    # Additionally, we include login URLs for the browsable API.
    url(r'^', include(router.urls)),
    url(r'^token/', api_views.getToken), # user token obtained in browser session
    url(r'^api-token-auth/', rest_views.obtain_auth_token), # user token obtained from command line
    # returns a JSON response when valid username and password fields are POSTed to the view using form data or JSON
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    # Always have default API view return current version
    url(r'^docs$', api_views.api_view, name="api")
]
