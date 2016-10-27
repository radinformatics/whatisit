from django.conf.urls import url, include
from django.conf import settings
from whatisit.apps.users import views as user_views
from social.apps.django_app import urls as social_urls

urlpatterns = [

    # Twitter, and social auth
    url(r'^login/$', user_views.login, name="login"),
    url(r'^accounts/login/$', user_views.login, name="login"),
    url(r'^home/$', user_views.home),
    url(r'^token/$', user_views.token, name="token"),
    url(r'^logout/$', user_views.logout, name="logout"),
    url('', include(social_urls, namespace='social'))

]
