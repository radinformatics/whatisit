from django.contrib.auth.models import User
from whatisit.apps.labelinator.models import Report, ReportCollection
from rest_framework import serializers


class ReportSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Report
        fields = ('uid', 'text')


class ReportCollectionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ReportCollection
        fields = ('name',)


class UserSerializer(serializers.ModelSerializer):
    collections = serializers.PrimaryKeyRelatedField(many=True, queryset=ReportCollection.objects.all())

    class Meta:
        model = User
        fields = ('id', 'username', 'collections')
