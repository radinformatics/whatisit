from django.conf.urls import url
from django.views.generic.base import TemplateView
import whatisit.apps.labelinator.views as report_views

urlpatterns = [

    # Reports
    url(r'^reports$', report_views.all_reports, name="report_collections"),
    url(r'^reports/(?P<coid>.+?)/new$', report_views.edit_report, name="upload_reports"),

    # Upload reports to a collection
    url(r'^reports/(?P<rid>.+?)/$',report_views.view_report,name='report_details'),
    url(r'^reports/(?P<cid>.+?)/save$',report_views.upload_report,name='save_reports'),

    # Report Collections
    url(r'^collections/new$',report_views.edit_report_collection,name='new_report_collection'),
    url(r'^collections/(?P<cid>.+?)/$',report_views.view_report_collection,name='report_collection_details'),
    url(r'^collections/(?P<cid>.+?)/count$',report_views.summarize_reports,name='report_collection_summary'),
    url(r'^collections/(?P<cid>.+?)/markup$',report_views.save_collection_markup,name='save_collection_markup'),
    url(r'^collections/(?P<cid>.+?)/edit$',report_views.edit_report_collection,name='edit_report_collection'),
    url(r'^collections/my$',report_views.my_report_collections,name='my_report_collections'),

    # Do annotations
    url(r'^annotate/reports/(?P<cid>.+?)/random$',report_views.annotate_random,name='annotate_random'),   # getrandom
    url(r'^annotate/reports/(?P<rid>.+?)/annotate$',report_views.annotate_report,name='annotate_report'), # showrandom
    url(r'^annotate/reports/(?P<cid>.+?)/curated$',report_views.annotate_curated,name='annotate_curated'),
    url(r'^annotate/reports/(?P<cid>.+?)/custom$',report_views.annotate_custom,name='annotate_custom'),

    # Update annotations
    url(r'^annotate/reports/(?P<rid>.+?)/update$',report_views.update_annotation,name='update_annotation'), # getrandom
]
