import pytz
import datetime
from urllib import unquote

from django.contrib import admin
from django.utils import timezone


from schedule.models import Calendar, Event, Occurrence, CalendarRelation, Rule, LivestreamUrl
from schedule.forms import EventAdminForm, OccurrenceAdminForm


class CalendarAdminOptions(admin.ModelAdmin):
    list_display = ('name', 'slug', 'station', 'timezone')
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ['name', 'station__name']
    fieldsets = (
        (None, {
            'fields': [
                ('name', 'slug','station', 'timezone'),
            ]
        }),
    )

class LivestreamUrlAdmin(admin.ModelAdmin):
    list_display = ('url', 'station')
    list_filter = ('station',)
    search_fields = ['url', 'station__name']
    fieldsets = (
        (None, {
            'fields': [
                ('url', 'station'),
            ]
        }),
    )


class CalendarRelationAdmin(admin.ModelAdmin):
    list_display = ('calendar', 'content_object')
    list_filter = ('inheritable',)
    fieldsets = (
        (None, {
            'fields': [
                'calendar',
                ('content_type', 'object_id', 'distinction',),
                'inheritable',
            ]
        }),
    )


class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_in_timezone', 'event_timezone',
        'end_in_timezone', 'calendar', 'rule', 'end_recurring_period',
        'updated_on', 'pk' )
    list_filter = ('calendar__station','calendar', 'start', 'rule', 'end_recurring_period')
    ordering = ('-updated_on',)
    date_hierarchy = 'start'
    search_fields = ('title', 'description')
    fieldsets = (
        (None, {
            'fields': [
                ('title',),
                ('description',),
                ('livestreamUrl'),
                ('start', 'end'),
                ('creator', 'calendar',),
                ('rule', 'end_recurring_period'),
            ]
        }),
    )
    form = EventAdminForm

    def event_timezone(self, event):
        tz = event.calendar.timezone
        return datetime.datetime.now(tz).tzname()
    event_timezone.short_description = 'TZ'
    def start_in_timezone(self, event):
        """Display start time on the changelist in its own timezone"""
        dt = event.start.astimezone(event.calendar.timezone)
        return dt.strftime('%Y-%m-%d %H:%M')
    start_in_timezone.short_description = 'Start'
    def end_in_timezone(self, event):
        dt = event.end.astimezone(event.calendar.timezone)
        return dt.strftime('%Y-%m-%d %H:%M')
    end_in_timezone.short_description = 'End'

    """ EventAdmin Overrides """
    # Override add view to set the timezone before it is proccessed
    def add_view(self, request, form_url='', extra_context=None):
        if request.method == 'POST':
            calendar = Calendar.objects.get(pk=int(request.POST.get('calendar')))
            timezone.activate(calendar.timezone)
        return super(EventAdmin, self).add_view(request, form_url, extra_context)

    # Override the change view to  set the timezone before processing
    def change_view(self, request, object_id, form_url='', extra_context=None):
        if request.method == 'POST':
            calendar = Calendar.objects.get(pk=int(request.POST.get('calendar')))
            timezone.activate(calendar.timezone)
        else:
            obj = self.get_object(request, unquote(object_id))
            timezone.activate(obj.calendar.timezone)
        return super(EventAdmin, self).change_view(request, object_id, form_url, extra_context)

     # Override queries to be restricted to user station affiliations
    def get_queryset(self, request):
        qs = super(EventAdmin, self).get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(calendar__station__in=request.user.stations.all())
        return qs
    # Override options for Calendar and LivestreamUrl on Event add form
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "calendar" and not request.user.is_superuser:
            kwargs["queryset"] = Calendar.objects.filter(station__in=request.user.stations.all())
            return db_field.formfield(**kwargs)
        if db_field.name == "livestreamUrl" and not request.user.is_superuser:
            kwargs["queryset"] = LivestreamUrl.objects.filter(station__in=request.user.stations.all())
            return db_field.formfield(**kwargs)
        return super(EventAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

class OccurrenceAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_in_timezone', 'event_timezone', 'end_in_timezone', 'cancelled','event', 'updated_on')
    list_filter = ('event__calendar__station', 'event__calendar', 'cancelled', 'start')
    fieldsets =(
        (None, {
            'fields': [
                ('event',),
                ('title',),
                ('description'),
                ('livestreamUrl'),
                ('start', 'end'),
                ('cancelled')
            ]
        }),
    )
    form = OccurrenceAdminForm
    def event_timezone(self, occurrence):
        tz = occurrence.event.calendar.timezone
        return datetime.datetime.now(tz).tzname()
    event_timezone.short_description = 'TZ'
    def start_in_timezone(self, occurrence):
        """Display start time on the changelist in its own timezone"""
        dt = occurrence.start.astimezone(occurrence.event.calendar.timezone)
        return dt.strftime('%Y-%m-%d %H:%M')
    start_in_timezone.short_description = 'Start'
    def end_in_timezone(self, occurrence):
        dt = occurrence.end.astimezone(occurrence.event.calendar.timezone)
        return dt.strftime('%Y-%m-%d %H:%M')
    end_in_timezone.short_description = 'End'

    """ OccurrenceAdmin Overrides"""
    # Override add view to set the timezone before it is proccessed
    def add_view(self, request, form_url='', extra_context=None):
        if request.method == 'POST':
            event = Event.objects.get(pk=int(request.POST.get('event')))
            timezone.activate(event.calendar.timezone)
        return super(OccurrenceAdmin, self).add_view(request, form_url, extra_context)

    # Override the change view to  set the timezone before processing
    def change_view(self, request, object_id, form_url='', extra_context=None):
        if request.method == 'POST':
            event = Event.objects.get(pk=int(request.POST.get('event')))
            timezone.activate(event.calendar.timezone)
        else:
            obj = self.get_object(request, unquote(object_id))
            timezone.activate(obj.calendar.timezone)
        return super(OccurrenceAdmin, self).change_view(request, object_id, form_url, extra_context)

    # Override queries to be restricted to user station affiliations
    def get_queryset(self, request):
        qs = super(OccurrenceAdmin, self).get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(event__calendar__station__in=request.user.stations.all())
        return qs
    # Override options for Event, LivestreamUrl
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "event" and not request.user.is_superuser:
            kwargs["queryset"] = Event.objects.filter(calendar__station__in=request.user.stations.all())
            return db_field.formfield(**kwargs)
        if db_field.name == "livestreamUrl" and not request.user.is_superuser:
            kwargs["queryset"] = LivestreamUrl.objects.filter(station__in=request.user.stations.all())
            return db_field.formfield(**kwargs)
        return super(OccurrenceAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

class RuleAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_filter = ('frequency',)
    search_fields = ('name', 'description')


admin.site.register(LivestreamUrl, LivestreamUrlAdmin)
admin.site.register(Calendar, CalendarAdminOptions)
admin.site.register(Event, EventAdmin)
admin.site.register(Occurrence, OccurrenceAdmin)
admin.site.register(Rule, RuleAdmin)
# admin.site.register(CalendarRelation, CalendarRelationAdmin)
