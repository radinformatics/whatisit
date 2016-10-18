from django.conf.urls import url
from django.views.generic.base import TemplateView
import whatisit.apps.labelinator.views as report_views

urlpatterns = [

    # Reports
    url(r'^reports$', report_views.all_reports, name="report_collections"),
    url(r'^reports/(?P<coid>.+?)/new$', report_views.edit_report, name="upload_reports"),

    # Upload reports to a collection
    url(r'^reports/(?P<cid>.+?)/$',report_views.view_report,name='report_details'),
    url(r'^reports/(?P<cid>.+?)/save$',report_views.upload_report,name='save_reports'),

    # report Collections
    url(r'^collections/reports/new$',report_views.edit_report_collection,name='new_report_collection'),
    url(r'^collections/reports/(?P<cid>.+?)/$',report_views.view_report_collection,name='report_collection_details'),
    url(r'^collections/reports/(?P<cid>.+?)/edit$',report_views.edit_report_collection,name='edit_report_collection'),
    url(r'^collections/reports/my$',report_views.my_report_collections,name='my_report_collections'),

]
