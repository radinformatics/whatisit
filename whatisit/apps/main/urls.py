from django.views.generic.base import (
    TemplateView,
    RedirectView
)
from django.conf.urls import url
import whatisit.apps.main.views as main_views

favicon_view = RedirectView.as_view(url='/static/img/favicon/favicon.ico', 
                                    permanent=True)

urlpatterns = [
    url(r'^$', main_views.index_view, name="index"),
    url(r'^about$', main_views.about_view, name="about"),
    url(r'^favicon\.ico$', favicon_view)
]
