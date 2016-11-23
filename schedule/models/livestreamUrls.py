from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _


from stations.models import Station

class LivestreamUrl(models.Model):
    url = models.URLField(max_length=300)
    station = models.ForeignKey(Station, help_text=_("The station who owns this url"))

    def __str__(self):
        return self.url

    class Meta:
        app_label = 'schedule'
        verbose_name = 'livestreamUrl'
        verbose_name_plural = 'livestreamUrls'
