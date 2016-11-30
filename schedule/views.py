import pytz
import datetime
import dateutil.parser
from django.utils.six.moves.urllib.parse import quote

from django.db.models import Q, F
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import HttpResponseRedirect, Http404, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import DetailView
from django.views.generic.edit import (
    UpdateView, CreateView, DeleteView, ModelFormMixin, ProcessFormView)
from django.utils.http import is_safe_url
from django.conf import settings

from schedule.conf.settings import (GET_EVENTS_FUNC, OCCURRENCE_CANCEL_REDIRECT,
                                    EVENT_NAME_PLACEHOLDER, CHECK_EVENT_PERM_FUNC,
                                    CHECK_OCCURRENCE_PERM_FUNC, USE_FULLCALENDAR)
from schedule.forms import EventForm, OccurrenceForm
from schedule.models import Calendar, Occurrence, Event
from schedule.periods import weekday_names
from schedule.utils import (
    check_event_permissions,
    check_calendar_permissions,
    coerce_date_dict,
    check_occurrence_permissions,
    calendar_view_permissions)
from schedule.templatetags.scheduletags import querystring_for_date


class CalendarViewPermissionMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(CalendarViewPermissionMixin, cls).as_view(**initkwargs)
        return calendar_view_permissions(view)


class EventEditPermissionMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(EventEditPermissionMixin, cls).as_view(**initkwargs)
        return check_event_permissions(view)


class OccurrenceEditPermissionMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(OccurrenceEditPermissionMixin, cls).as_view(**initkwargs)
        return check_occurrence_permissions(view)


class CancelButtonMixin(object):
    def post(self, request, *args, **kwargs):
        next_url = kwargs.get('next')
        self.success_url = get_next_url(request, next_url)
        if "cancel" in request.POST:
            return HttpResponseRedirect(self.success_url)
        else:
            return super(CancelButtonMixin, self).post(request, *args, **kwargs)


class CalendarMixin(CalendarViewPermissionMixin):
    model = Calendar
    slug_url_kwarg = 'calendar_slug'


class CalendarView(CalendarMixin, DetailView):
    template_name = 'schedule/calendar.html'

    def get_context_data(self, **kwargs):
        context = super(CalendarView, self).get_context_data()
        calendar_slug = self.kwargs['calendar_slug']
        calendar = Calendar.objects.get(slug=calendar_slug)
        context['calendar'] = calendar
        context['events_count'] = len(calendar.events.all())
        return context


class FullCalendarView(CalendarMixin, DetailView):
    template_name = "fullcalendar.html"

    def get_context_data(self, **kwargs):
        context = super(FullCalendarView, self).get_context_data()
        context['calendar_slug'] = self.kwargs.get('calendar_slug')
        return context


class CalendarByPeriodsView(CalendarMixin, DetailView):
    template_name = 'schedule/calendar_by_period.html'

    def get_context_data(self, **kwargs):
        context = super(CalendarByPeriodsView, self).get_context_data(**kwargs)
        calendar = self.object
        period_class = self.kwargs['period']
        try:
            date = coerce_date_dict(self.request.GET)
        except ValueError:
            raise Http404
        if date:
            try:
                date = datetime.datetime(**date)
            except ValueError:
                raise Http404
        else:
            date = timezone.now()
        event_list = GET_EVENTS_FUNC(self.request, calendar)

        # local_timezone = timezone.get_current_timezone()
        period = period_class(event_list, date)#, tzinfo=local_timezone)

        context.update({
            'date': date,
            'period': period,
            'calendar': calendar,
            'weekday_names': weekday_names,
            'here': quote(self.request.get_full_path()),
        })
        return context


class OccurrenceMixin(CalendarViewPermissionMixin, TemplateResponseMixin):
    model = Occurrence
    pk_url_kwarg = 'occurrence_id'
    form_class = OccurrenceForm


class OccurrenceEditMixin(OccurrenceEditPermissionMixin, OccurrenceMixin):
    def get_initial(self):
        initial_data = super(OccurrenceEditMixin, self).get_initial()
        _, self.object = get_occurrence(**self.kwargs)
        return initial_data

    def get_context_data(self, **kwargs):
        event, occurrence = get_occurrence(**self.kwargs)
        context = super(OccurrenceEditMixin, self).get_context_data()
        context['event'] = event
        context['occurrence'] = occurrence
        return context

    def post(self, request, *args, **kwargs):
        _, occurrence = get_occurrence(**kwargs)
        if "cancel" in request.POST:
            return HttpResponseRedirect(reverse('day_calendar',
                kwargs={'calendar_slug':occurrence.event.calendar.slug})
                + querystring_for_date(occurrence.start, 3)) # send user back to day calendar for occurrence start date
        else:
            return super(OccurrenceEditMixin, self).post(request, *args, **kwargs)


class OccurrenceView(OccurrenceMixin, DetailView):
    template_name = 'schedule/occurrence.html'


class OccurrencePreview(OccurrenceMixin, ModelFormMixin, ProcessFormView):
    template_name = 'schedule/occurrence.html'

    def get_context_data(self, **kwargs):
        context = super(OccurrencePreview, self).get_context_data()
        context = {
            'event': self.object.event,
            'occurrence': self.object,
        }
        return context


class EditOccurrenceView(OccurrenceEditMixin, UpdateView):
    template_name = 'schedule/edit_occurrence.html'



class CreateOccurrenceView(OccurrenceEditMixin, CreateView):
    template_name = 'schedule/edit_occurrence.html'


class CancelOccurrenceView(OccurrenceEditMixin, ModelFormMixin, ProcessFormView):
    template_name = 'schedule/cancel_occurrence.html'

    def post(self, request, *args, **kwargs):
        event, occurrence = get_occurrence(**kwargs)
        self.success_url = kwargs.get(
            'next',
            get_next_url(request, event.get_absolute_url()))
        if "cancel" not in request.POST:
            occurrence.cancel()
        return HttpResponseRedirect(self.success_url)


class EventMixin(CalendarViewPermissionMixin):
    model = Event
    pk_url_kwarg = 'event_id'


class EventEditMixin(EventEditPermissionMixin, EventMixin):
    pass

class EventView(EventMixin, DetailView):
    template_name = 'schedule/event.html'
    def get_context_data(self, **kwargs):
        context = super(EventView, self).get_context_data(**kwargs)
        event = Event.objects.get(pk=self.kwargs['event_id'])
        context['can_edit'] = CHECK_EVENT_PERM_FUNC(event, self.request.user)
        return context



class EditEventView(EventEditMixin, UpdateView):
    # def get_form_class(self):
    #     event = self.get_object()
    #     if event.occurrence_set.all(): #if there are any persisted occurrences
    #         return EditEventForm
    #     else:
    #         return EventForm
    form_class = EventForm
    template_name = 'schedule/create_event.html'

    def get_initial(self):
        initial_data = {
            "calendar": Calendar.objects.get(slug=self.kwargs['calendar_slug']),
            "event_id": self.kwargs['event_id']
            }
        return initial_data

    def form_valid(self, form):
        event = form.save(commit=False)
        old_event = Event.objects.get(pk=event.pk)
        dts = datetime.timedelta(
            minutes=int((event.start - old_event.start).total_seconds() / 60)
        )
        dte = datetime.timedelta(
            minutes=int((event.end - old_event.end).total_seconds() / 60)
        )
        # event.occurrence_set.all().update(
        #     original_start=F('original_start') + dts,
        #     original_end=F('original_end') + dte,
        # )
        for occ in event.occurrence_set.all():
            occ.original_start = occ.original_start + dts
            occ.original_end = occ.original_end + dte

        event.save()
        return super(EditEventView, self).form_valid(form)

    def post(self, request, *args, **kwargs):
        event = Event.objects.get(pk=self.kwargs['event_id'])
        if "cancel" in request.POST:
            return HttpResponseRedirect(event.get_absolute_url()) # redirect to event if action cancelled
        else:
            return super(EditEventView, self).post(request, *args, **kwargs)


class CreateEventView(EventEditMixin, CreateView):
    form_class = EventForm
    template_name = 'schedule/create_event.html'

    def get_initial(self):
        date = coerce_date_dict(self.request.GET)
        initial_data = None
        if date:
            try:
                start = datetime.datetime(**date)
                initial_data = {
                    "calendar": Calendar.objects.get(slug=self.kwargs['calendar_slug']),
                    "start": start,
                    "end": start + datetime.timedelta(minutes=30),
                }
            except TypeError:
                raise Http404
            except ValueError:
                raise Http404
        return initial_data

    def form_valid(self, form):
        event = form.save(commit=False)
        event.creator = self.request.user
        # event.calendar = get_object_or_404(Calendar, slug=self.kwargs['calendar_slug'])
        event.save()
        return HttpResponseRedirect(event.get_absolute_url())


class DeleteEventView(EventEditMixin, DeleteView):
    template_name = 'schedule/delete_event.html'

    def get_context_data(self, **kwargs):
        ctx = super(DeleteEventView, self).get_context_data(**kwargs)
        ctx['next'] = self.get_success_url()
        return ctx

    def get_success_url(self):
        """
        After the event is deleted there are three options for redirect, tried in
        this order:
        # Try to find a 'next' GET variable
        # If the key word argument redirect is set
        # Lastly redirect to the event detail of the recently create event
        """
        url_val = 'fullcalendar' if USE_FULLCALENDAR else 'day_calendar'
        next_url = self.kwargs.get('next') or reverse(url_val, args=[self.object.calendar.slug])
        next_url = get_next_url(self.request, next_url)
        return next_url


def get_occurrence(event_id, occurrence_id=None, year=None, month=None,
                   day=None, hour=None, minute=None, second=None,
                   tzinfo=pytz.utc):
    """
    Because occurrences don't have to be persisted, there must be two ways to
    retrieve them. both need an event, but if its persisted the occurrence can
    be retrieved with an id. If it is not persisted it takes a date to
    retrieve it.  This function returns an event and occurrence regardless of
    which method is used.
    """
    if(occurrence_id):
        occurrence = get_object_or_404(Occurrence, id=occurrence_id)
        event = occurrence.event
    elif(all((year, month, day, hour, minute, second))):
        event = get_object_or_404(Event, id=event_id)
        occurrence = event.get_occurrence(
            datetime.datetime(int(year), int(month), int(day), int(hour),
                              int(minute), int(second), tzinfo=tzinfo))
        if occurrence is None:
            raise Http404
    else:
        raise Http404
    return event, occurrence


def check_next_url(next_url):
    """
    Checks to make sure the next url is not redirecting to another page.
    Basically it is a minimal security check.
    """
    if not next_url or '://' in next_url:
        return None
    return next_url


def get_next_url(request, default):
    next_url = default
    if OCCURRENCE_CANCEL_REDIRECT:
        next_url = OCCURRENCE_CANCEL_REDIRECT
    _next_url = request.GET.get('next') if request.method in ['GET', 'HEAD'] else request.POST.get('next')
    if _next_url and is_safe_url(url=_next_url, host=request.get_host()):
        next_url = _next_url
    return next_url

def get_boolean_from_request(request, key, default=False):
    value = request.GET.get(key, None)
    if value in ['True', 'true', '1', 1]:
        return True
    elif value in ['False', 'false', '0', 0]:
        return False
    else:
        return default

def live_now(request):
    calendar_slug = request.GET.get('calendar_slug')
    # Get current local time
    calendar = Calendar.objects.get(slug=calendar_slug)
    tz = pytz.timezone(calendar.timezone.name)
    utc_now = datetime.datetime.utcnow()
    current_local = utc_now + tz.utcoffset(utc_now)
    start = current_local.replace(tzinfo=pytz.UTC)
    dt = datetime.timedelta(seconds=1)
    end = start + dt
    try:
        response_data = _api_occurrences(start, end, calendar_slug)
    except (ValueError, Calendar.DoesNotExist) as e:
        return HttpResponseBadRequest(e)
    return JsonResponse(response_data, safe=False)

def api_occurrences(request):
    start = request.GET.get('start')
    end = request.GET.get('end')
    calendar_slug = request.GET.get('calendar_slug')
    include_cancelled = get_boolean_from_request(request,
        'include_cancelled', default=False)

    if '-' in start:
        def convert(ddatetime):
            if ddatetime:
                ddatetime = ddatetime.split(' ')[0]
                return datetime.datetime.strptime(ddatetime, '%Y-%m-%d')
    else:
        def convert(ddatetime):
            return datetime.datetime.utcfromtimestamp(float(ddatetime))

    start = convert(start)
    end = convert(end)
    # If USE_TZ is True, make start and end dates aware in UTC timezone
    if settings.USE_TZ:
        utc = pytz.UTC
        start = utc.localize(start)
        end = utc.localize(end)
    try:
        response_data = _api_occurrences(start, end, calendar_slug,
            include_cancelled=include_cancelled)
    except (ValueError, Calendar.DoesNotExist) as e:
        return HttpResponseBadRequest(e)

    return JsonResponse(response_data, safe=False)

def _api_occurrences(start, end, calendar_slug, include_cancelled=False):
    if not start or not end:
        raise ValueError('Start and end parameters are required')

    if calendar_slug:
        # will raise DoesNotExist exception if no match
        calendars = [Calendar.objects.get(slug=calendar_slug)]
    # if no calendar slug is given, get all the calendars
    else:
        calendars = Calendar.objects.all()
    response_data = []
    # Algorithm to get an id for the occurrences in fullcalendar (NOT THE SAME
    # AS IN THE DB) which are always unique.
    # Fullcalendar thinks that all their "events" with the same "event.id" in
    # their system are the same object, because it's not really built around
    # the idea of events (generators)
    # and occurrences (their events).
    # Check the "persisted" boolean value that tells it whether to change the
    # event, using the "event_id" or the occurrence with the specified "id".
    # for more info https://github.com/llazzaro/django-scheduler/pull/169
    i = 1
    if Occurrence.objects.all().count() > 0:
        i = Occurrence.objects.latest('id').id + 1
    event_list = []
    for calendar in calendars:
        # create flat list of events from each calendar
        event_list += calendar.events.filter(start__lte=end).filter(
            Q(end_recurring_period__gte=start) |
            Q(end_recurring_period__isnull=True))
    for event in event_list:
        occurrences = event.get_occurrences(start, end)
        for occurrence in occurrences:
            if occurrence.cancelled and not include_cancelled:
                continue
            occurrence_id = i + occurrence.event.id
            existed = False

            if occurrence.id:
                occurrence_id = occurrence.id
                existed = True

            recur_rule = occurrence.event.rule.name \
                if occurrence.event.rule else None
            recur_period_end = \
                occurrence.event.end_recurring_period.isoformat() \
                if occurrence.event.end_recurring_period else None

            response_data.append({
                "id": occurrence_id,
                "title": occurrence.title,
                "start": occurrence.start.isoformat(),
                "end": occurrence.end.isoformat(),
                "existed": existed,
                "event_id": occurrence.event.id,
                "description": occurrence.description,
                "livestream_url": occurrence.livestreamUrl.url,
                "rule": recur_rule,
                "end_recurring_period": recur_period_end,
                "creator": str(occurrence.event.creator),
                "calendar": occurrence.event.calendar.slug,
                "cancelled": occurrence.cancelled,
            })
    return response_data



@require_POST
@check_calendar_permissions
def api_move_or_resize_by_code(request):
    response_data = {}
    user = request.user
    id = request.POST.get(id)
    existed = bool(request.POST.get('existed') == 'true')
    delta = datetime.timedelta(minutes=int(request.POST.get('delta')))
    resize = bool(request.POST.get('resize', False))
    event_id = request.POST.get('event_id')

    response_data = _api_move_or_resize_by_code(
        user,
        id,
        existed,
        delta,
        resize,
        event_id)

    return JsonResponse(response_data)


def _api_move_or_resize_by_code(user, id, existed, delta, resize, event_id):
    response_data = {}
    response_data['status'] = "PERMISSION DENIED"

    if existed:
        occurrence = Occurrence.objects.get(id=id)
        occurrence.end += delta
        if not resize:
            occurrence.start += delta
        if CHECK_OCCURRENCE_PERM_FUNC(occurrence, user):
            occurrence.save()
            response_data['status'] = "OK"
    else:
        event = Event.objects.get(id=event_id)
        dts = 0
        dte = delta
        if not resize:
            event.start += delta
            dts = delta
        event.end = event.end + delta
        if CHECK_EVENT_PERM_FUNC(event, user):
            event.save()
            # event.occurrence_set.all().update(
            #     original_start=F('original_start') + dts,
            #     original_end=F('original_end') + dte,
            # )
            for occ in event.occurrence_set.all():
                occ.original_start = occ.original_start + dts
                occ.original_end = occ.original_end + dte

            response_data['status'] = "OK"
    return response_data


@require_POST
@check_calendar_permissions
def api_select_create(request):
    response_data = {}
    start = request.POST.get('start')
    end = request.POST.get('end')
    calendar_slug = request.POST.get('calendar_slug')

    response_data = _api_select_create(start, end, calendar_slug)

    return JsonResponse(response_data)


def _api_select_create(start, end, calendar_slug):
    start = dateutil.parser.parse('start')
    end = dateutil.parser.parse('end')

    calendar = Calendar.objects.get(slug=calendar_slug)
    Event.objects.create(
        start=start,
        end=end,
        title=EVENT_NAME_PLACEHOLDER,
        calendar=calendar,
    )

    response_data = {}
    response_data['status'] = "OK"
    return response_data
