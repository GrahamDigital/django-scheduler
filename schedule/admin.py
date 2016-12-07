from django.contrib import admin

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
    list_display = ('title', 'start', 'end', 'calendar', 'rule', 'end_recurring_period', 'livestreamUrl', 'pk')
    list_filter = ('calendar__station','calendar', 'start', 'rule', 'end_recurring_period', 'livestreamUrl')
    ordering = ('-start',)
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
    list_display = ('title', 'start', 'end', 'cancelled','event', 'updated_on')
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
admin.site.register(CalendarRelation, CalendarRelationAdmin)
