from django import template

from schedule.models import Calendar

register = template.Library()

@register.assignment_tag
def schedule_allcalendars():
    return Calendar.objects.all()
