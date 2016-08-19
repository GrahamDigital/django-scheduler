from django import forms
from django.utils.translation import ugettext_lazy as _
from schedule.models import Event, Occurrence
from schedule.periods import Period
from schedule.widgets import SpectrumColorPicker
import datetime


class SpanForm(forms.ModelForm):
    start = forms.SplitDateTimeField(label=_("start"))
    end = forms.SplitDateTimeField(label=_("end"),
                                   help_text=_(u"The end time must be later than start time."))

    def clean(self):
        if 'end' in self.cleaned_data and 'start' in self.cleaned_data:
            if self.cleaned_data['end'] <= self.cleaned_data['start']:
                raise forms.ValidationError(_(u"The end time must be later than start time!"))
        return self.cleaned_data


class EventForm(SpanForm):
    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)

    end_recurring_period = forms.DateTimeField(label=_(u"End recurring period"),
                                               help_text=_(u"This date is ignored for one time only events."),
                                               required=False)

    class Meta(object):
        model = Event
        exclude = ('creator', 'created_on', 'calendar')


class OccurrenceForm(SpanForm):
    class Meta(object):
        model = Occurrence
        exclude = ('original_start', 'original_end', 'event', )


class EventAdminForm(forms.ModelForm):
    def clean(self):
        super(EventAdminForm, self).clean() # clean the form data
        check_event_conflicts(self)
        return self.cleaned_data

    class Meta:
        exclude = []
        model = Event
        widgets = {
            'color_event': SpectrumColorPicker,
        }

# """ Validation Functions """
def time_conflicts(start1,end1,start2,end2):
    if start2 <= start1 < end2: # if start in range (allow start1 = end2)
        return True
    if start2 < end1 <= end2: # if end in range (allow end1 = start2)
        return True
    if (start2 <= start1) and (end1 <= end2): # if (start1,end1) contained in (start2, end2)
        return True
    return False


def check_occ_conflicts(occ, events):
    period =Period(events, occ.start, occ.end)
    for pocc in period.occurrences:
        if not pocc.cancelled:
            if time_conflicts(occ.start, occ.end, pocc.start, pocc.end):
                raise forms.ValidationError(
            """ Conflicts with an Occurrence of Event %(title)s (pk = %(pk)s)!
            Conflicting occurrence runs %(starttime)s -- %(endtime)s. """%{
            'title': occ.title,
            'pk': occ.event.pk,
            'starttime': occ.start.strftime('%a %Y-%m-%d %H:%M'),
            'endtime': occ.end.strftime('%a %Y-%m-%d %H:%M')})

def check_event_conflicts(self):
    calendar = self.cleaned_data.get('calendar')
    start = self.cleaned_data.get('start')
    end = self.cleaned_data.get('end')
    rule = self.cleaned_data.get('rule')
    end_recurring_period = self.cleaned_data.get('end_recurring_period')
    primKey = self.instance.pk #Instance primary key

    if 'end' in self.cleaned_data and 'start' in self.cleaned_data:
        if self.cleaned_data['end'] <= self.cleaned_data['start']:
            raise forms.ValidationError(_(u"The end time must be later than start time!"))

    if rule and not end_recurring_period:
        raise forms.ValidationError(_(u"Recurring Events (with rules) must have a value for 'End Recurring Period'!"))

    events = Event.objects.filter(calendar = calendar)
    if primKey: #exclude self if instance exists
        events.exclude(pk=primKey)

    event = Event(calendar=calendar, start=start, end=end, rule=rule, end_recurring_period=end_recurring_period, title='placeholder')
    if not rule : # If not a recurring event, straightforward to find all possible conflicts
        occ =event.get_occurrence(event.start)
        check_occ_conflicts(occ, events)
    elif rule:
        event = Event(calendar=calendar, start=start, end=end, rule=rule, end_recurring_period=end_recurring_period, title='placeholder')
        e_occs = event.get_occurrences(start, end_recurring_period)
        for occ in e_occs:
            check_occ_conflicts(occ, events)
