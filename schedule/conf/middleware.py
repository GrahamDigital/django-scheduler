from django.utils import timezone
import pytz

class TimezoneMiddleware(object):
    def process_request(self, request):
        # Set timezone to UTC depending on request url path
        path = request.path_info
        split_path = path.split('/')
        if 'schedule' in [split_path[0], split_path[1]]:
            tz = pytz.timezone('UTC')

        if tz:
            timezone.activate(tz)
        else:
            timezone.deactivate()
