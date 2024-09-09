from .models import Notification

def notification_processor(request):
    notifications = Notification.objects.filter(is_read=False)
    return {'notifications': notifications}