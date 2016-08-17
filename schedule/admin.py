from django.contrib import admin

from schedule.models import Calendar, Event, CalendarRelation, Rule
from schedule.forms import EventAdminForm


class CalendarAdminOptions(admin.ModelAdmin):
    list_display = ('name', 'slug', 'station')
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ['name', 'station__name']
    fieldsets = (
        (None, {
            'fields': [
                ('name', 'slug','station'),
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
    list_display = ('title', 'start', 'end', 'calendar', 'rule', 'end_recurring_period')
    list_filter = ('calendar__station','calendar', 'start', 'rule', 'end_recurring_period')
    ordering = ('-start',)
    date_hierarchy = 'start'
    search_fields = ('title', 'description')
    fieldsets = (
        (None, {
            'fields': [
                ('title', 'color_event'),
                ('description',),
                ('start', 'end'),
                ('creator', 'calendar'),
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
    # Override options for station on Program add form
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "calendar" and not request.user.is_superuser:
            kwargs["queryset"] = Calendar.objects.filter(station__in=request.user.stations.all())
            return db_field.formfield(**kwargs)
        return super(EventAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class RuleAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_filter = ('frequency',)
    search_fields = ('name', 'description')


admin.site.register(Calendar, CalendarAdminOptions)
admin.site.register(Event, EventAdmin)
admin.site.register(Rule, RuleAdmin)
admin.site.register(CalendarRelation, CalendarRelationAdmin)
