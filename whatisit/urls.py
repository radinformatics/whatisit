"""shub URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
"""
from django.conf.urls import include, url
from whatisit.apps.main import urls as main_urls
from whatisit.apps.labelinator import urls as labelinator_urls
from whatisit.apps.users import urls as user_urls
from whatisit.apps.api import urls as api_urls

from django.contrib import admin
from django.contrib.sitemaps.views import sitemap, index

# Configure custom error pages
from django.conf.urls import ( handler404, handler500 )
handler404 = 'whatisit.apps.main.views.handler404'
handler500 = 'whatisit.apps.main.views.handler500'

# Sitemaps
from whatisit.apps.api.sitemap import ReportCollectionSitemap, ReportSitemap
sitemaps = {"containers":ReportSitemap,
            "collections":ReportCollectionSitemap}

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include(main_urls)),
    url(r'^api/', include(api_urls)),
    url(r'^', include(labelinator_urls)),
    url(r'^', include(user_urls)),
    url(r'^sitemap\.xml$', index, {'sitemaps': sitemaps}, name="sitemap"),
    url(r'^sitemap-(?P<section>.+)\.xml$', sitemap, {'sitemaps': sitemaps}),
]
