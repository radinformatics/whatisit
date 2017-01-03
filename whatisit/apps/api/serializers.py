from django.contrib.auth.models import User
from whatisit.apps.wordfish.models import (
    Annotation,
    AllowedAnnotation,
    Report, 
    ReportCollection,
    ReportSet
)

from rest_framework import serializers

class ReportSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Report
        fields = ('report_id', 'report_text')


class SingleReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = Report
        fields = ('report_id','report_text')


class ReportCollectionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ReportCollection
        fields = ('name',)


class ReportSetSerializer(serializers.HyperlinkedModelSerializer):
    reports = serializers.PrimaryKeyRelatedField(many=True, queryset=Report.objects.all())
    class Meta:
        model = ReportSet
        fields = ('name','reports')


#class UserSerializer(serializers.ModelSerializer):
#    collections = serializers.PrimaryKeyRelatedField(many=True, queryset=ReportCollection.objects.all())#
#    class Meta:
#        model = User
#        fields = ('id', 'username', 'collections')
