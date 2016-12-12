from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _


from stations.models import Station

class LivestreamUrl(models.Model):
    url = models.URLField(max_length=1000, help_text=_("The stream url to be embedded"))
    name = models.CharField(_("name"), max_length=200, null=True, blank=True, help_text=_("A reference name for the stream"))
    station = models.ForeignKey(Station, help_text=_("The station who owns this url"))

    def __str__(self):
        if self.name:
            return self.name
        else:
            return self.url

    class Meta:
        app_label = 'schedule'
        verbose_name = 'livestreamUrl'
        verbose_name_plural = 'livestreamUrls'
