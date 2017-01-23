from django import template

from schedule.models import Calendar, LivestreamUrl

register = template.Library()

@register.assignment_tag
def schedule_allcalendars():
    return Calendar.objects.all()

@register.assignment_tag
def schedule_alllivestreams():
    return LivestreamUrl.objects.all()
