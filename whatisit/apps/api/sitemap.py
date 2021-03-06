from django.contrib.sitemaps import Sitemap
from whatisit.apps.wordfish.models import Report, ReportCollection

class BaseSitemap(Sitemap):
    priority = 0.5
    def location(self,obj):
        return obj.get_absolute_url()


class ReportSitemap(BaseSitemap):
    changefreq = "weekly"
    def items(self):
        return [x for x in Report.objects.all() if x.collection.private == False]

class ReportCollectionSitemap(BaseSitemap):
    changefreq = "weekly"
    def items(self):
        return [x for x in ReportCollection.objects.all() if x.private == False]
