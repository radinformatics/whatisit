from django.conf.urls import url
from django.views.generic.base import TemplateView
import whatisit.apps.tagtrout.views as doc_views

urlpatterns = [

    # docs
    url(r'^collections/docs$', doc_views.view_docs_collections, name="docs_collections"),
    url(r'^doc/(?P<did>.+?)/details$',doc_views.view_doc,name='doc_details'),

    # Docs Collections
    url(r'^docs/collections/(?P<did>.+?)/$',doc_views.view_docs_collection,name='doc_collection_details'),
    url(r'^docs/collections/(?P<did>.+?)/edit$',doc_views.edit_docs_collection,name='edit_doc_collection'),
    url(r'^docs/collections/my$',doc_views.my_docs_collections,name='my_doc_collections'),

    # Change / add contributors
    url(r'^docs/contributors/(?P<did>.+?)/(?P<uid>.+?)/remove$',doc_views.remove_contributor,name='remove_contributor'),
    url(r'^docs/contributors/(?P<did>.+?)/add$',doc_views.add_contributor,name='add_contributor'),
    url(r'^docs/contributors/(?P<did>.+?)/edit$',doc_views.edit_contributors,name='edit_contributors'),


]
