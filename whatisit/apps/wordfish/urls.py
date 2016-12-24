from django.conf.urls import url
from django.views.generic.base import TemplateView
import whatisit.apps.wordfish.views as report_views
import whatisit.apps.wordfish.tests as test_views

urlpatterns = [

    # Reports
    url(r'^collections/reports$', report_views.view_report_collections, name="report_collections"),
    url(r'^reports/(?P<coid>.+?)/new$', report_views.upload_reports, name="upload_reports"),
    url(r'^reports/(?P<rid>.+?)/details$',report_views.view_report,name='report_details'),

    # Report Collections
    url(r'^collections/new$',report_views.edit_report_collection,name='new_report_collection'),
    url(r'^collections/(?P<cid>.+?)/$',report_views.view_report_collection,name='report_collection_details'),
    url(r'^collections/(?P<cid>.+?)/count$',report_views.summarize_reports,name='report_collection_summary'),
    url(r'^collections/(?P<cid>.+?)/markup$',report_views.save_collection_markup,name='save_collection_markup'),
    url(r'^collections/(?P<cid>.+?)/edit$',report_views.edit_report_collection,name='edit_report_collection'),
    url(r'^collections/my$',report_views.my_report_collections,name='my_report_collections'),
    url(r'^collections/(?P<sid>.+?)/sets/annotators$',report_views.edit_set_annotators,name='edit_set_annotators'),

    # Annotation Labels
    url(r'^labels/reports/(?P<cid>.+?)/(?P<lid>.+?)/new$',report_views.create_label,name='create_label'), # from existing
    url(r'^labels/reports/(?P<cid>.+?)/new$',report_views.create_label,name='create_label'), # create new label
 
    # Annotation sets
    url(r'^filter/(?P<cid>.+?)/create$',report_views.create_annotation_set,name='create_annotation_set'),
    url(r'^filter/(?P<cid>.+?)/save$',report_views.save_annotation_set,name='save_annotation_set'),

    # Annotations
    url(r'^annotate/reports/(?P<cid>.+?)/random$',report_views.annotate_random,name='annotate_random'),   # getrandom
    url(r'^annotate/reports/(?P<rid>.+?)/(?P<sid>.+?)/annotate$',report_views.annotate_report,name='annotate_report'), # set
    url(r'^annotate/reports/(?P<rid>.+?)/annotate$',report_views.annotate_report,name='annotate_report'), # showrandom
    url(r'^annotate/reports/(?P<sid>.+?)/set$',report_views.annotate_set,name='annotate_set'),

    # Bulk Annotations
    url(r'^bulk/reports/(?P<cid>.+?)/(?P<sid>.+?)/annotate$',report_views.bulk_annotate,name='bulk_annotate'), # set
    url(r'^bulk/reports/(?P<cid>.+?)/annotate$',report_views.bulk_annotate,name='bulk_annotate'), # collection

    # Request Addition to collection
    url(r'^annotate/(?P<cid>.+?)/request$',report_views.request_annotate_permission,name='request_annotate_permission'),
    url(r'^annotate/(?P<cid>.+?)/(?P<uid>.+?)/approve$',report_views.approve_annotate_permission,
                                                                name='approve_annotator'),
    url(r'^annotate/(?P<cid>.+?)/(?P<uid>.+?)/denied$',report_views.deny_annotate_permission,
                                                                name='deny_annotator'),

    # Change annotator access to report_set
    url(r'^set/annotate/(?P<sid>.+?)/(?P<uid>.+?)/approve$',report_views.approve_set_annotator,name='approve_set_annotator'),
    url(r'^set/annotate/(?P<sid>.+?)/(?P<uid>.+?)/deny$',report_views.deny_set_annotator,name='deny_set_annotator'),
    url(r'^set/annotate/(?P<sid>.+?)/(?P<uid>.+?)/test$',report_views.test_set_annotator,name='test_set_annotator'),
    url(r'^set/annotate/(?P<sid>.+?)/(?P<uid>.+?)/remove$',report_views.remove_set_annotator,name='remove_set_annotator'),
    url(r'^set/annotate/(?P<sid>.+?)/test$',report_views.new_set_annotator,name='new_set_annotator'), #same as test, from post

    # Change / add contributors
    url(r'^contributors/(?P<cid>.+?)/(?P<uid>.+?)/remove$',report_views.remove_contributor,name='remove_contributor'),
    url(r'^contributors/(?P<cid>.+?)/add$',report_views.add_contributor,name='add_contributor'),
    url(r'^contributors/(?P<cid>.+?)/edit$',report_views.edit_contributors,name='edit_contributors'),

    # Update/clear annotations
    url(r'^annotate/reports/(?P<rid>.+?)/update$',report_views.update_annotation,name='update_annotation'), # getrandom
    url(r'^annotate/reports/(?P<rid>.+?)/clear$',report_views.clear_annotations,name='clear_annotations'),

    # Testing
    url(r'^annotate/reports/(?P<sid>.+?)/(?P<rid>.+?)/test$',test_views.test_annotator,name='test_annotator'),
    url(r'^testing/reports/(?P<rid>.+?)/(?P<sid>.+?)/annotate$',report_views.annotate_report,name='annotate_report_testing'), # set
    url(r'^testing/reports/(?P<rid>.+?)/annotate$',report_views.annotate_report,name='annotate_report_testing'),

]
