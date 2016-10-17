from django.views.generic.base import TemplateView
from django.conf.urls import url
import whatisit.apps.main.views as main_views

urlpatterns = [
    url(r'^$', main_views.index_view, name="index"),
    url(r'^about$', main_views.about_view, name="about")
]
