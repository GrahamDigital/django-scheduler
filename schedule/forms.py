from django import forms
from django.utils.translation import ugettext_lazy as _
from schedule.models import Event, Occurrence, Calendar, Rule
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

class EventForm(SpanForm):
    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        calendar = kwargs['initial']['calendar']
        self.fields['calendar'].queryset = Calendar.objects.filter(slug=calendar.slug) # restrict calendar choice to only the calendar passed through the url
        if 'event_id' in kwargs['initial']:
            event = Event.objects.get(pk=kwargs['initial']['event_id'])
            self.fields['rule'].queryset = Rule.objects.filter(name=event.rule.name) # don't allow rule changes for saved events (breaks the generation of persisted occurrences)

    end_recurring_period = forms.DateTimeField(label=_(u"End recurring period"),
                                               help_text=_(u"This date is ignored for one time only events."),
                                               required=False)
    def clean(self):
        super(EventForm, self).clean() # clean the form data
        check_event_conflicts(self)
        return self.cleaned_data

    class Meta(object):
        model = Event
        exclude = ('created_on', 'creator')

# """ Validation Functions """
def time_conflicts(start1,end1,start2,end2):
    """
    Given two occurrences with start/end datetimes (start1,end1) & (start2,end2),
    checks to see if there is any overlap in their runtimes.
    Returns False if there is no conflict.
    """
    if start2 <= start1 < end2: # if start in range (allow start1 = end2)
        return True
    if start2 < end1 <= end2: # if end in range (allow end1 = start2)
        return True
    if (start2 <= start1) and (end1 <= end2): # if (start1,end1) contained in (start2, end2)
        return True
    return False


def check_occ_conflicts(occ, events):
    """
    Checks to see if an occurrence (occ) conflicts with any occurrence of an
    event queryset (events).
    """
    period =Period(events, occ.start, occ.end)
    for pocc in period.occurrences:
        if not pocc.cancelled:
            if time_conflicts(occ.start, occ.end, pocc.start, pocc.end):
                raise forms.ValidationError(
            """ Conflicts with an Occurrence of Event '%(title)s' (id = %(pk)s)!
            Conflicting occurrence runs %(starttime)s -- %(endtime)s. """%{
            'title': pocc.title,
            'pk': pocc.event.pk,
            'starttime': pocc.start.strftime('%a %Y-%m-%d %H:%M'),
            'endtime': pocc.end.strftime('%a %Y-%m-%d %H:%M')})

def check_event_conflicts(form):
    calendar = form.cleaned_data.get('calendar')
    start = form.cleaned_data.get('start')
    end = form.cleaned_data.get('end')
    rule = form.cleaned_data.get('rule')
    end_recurring_period = form.cleaned_data.get('end_recurring_period')
    primKey = form.instance.pk #Instance primary key

    if 'end' in form.cleaned_data and 'start' in form.cleaned_data:
        if form.cleaned_data['end'] <= form.cleaned_data['start']:
            raise forms.ValidationError(_(u"The end time must be later than start time!"))

    if rule and not end_recurring_period:
        raise forms.ValidationError(_(u"Recurring Events (with rules) must have a value for 'End Recurring Period'!"))

    events = Event.objects.filter(calendar = calendar)
    if primKey: #exclude self if instance exists
        events = events.exclude(pk=primKey)

    event = Event(calendar=calendar, start=start, end=end, rule=rule, end_recurring_period=end_recurring_period, title='temp_placeholder')
    if not rule :
        occ =event.get_occurrence(event.start)
        check_occ_conflicts(occ, events)
    elif rule:
        e_occs = event.get_occurrences(start, end_recurring_period)
        for occ in e_occs:
            check_occ_conflicts(occ, events)
