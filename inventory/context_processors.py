import datetime
from loguru import logger
from .models import Notification, CheckList

def notification_processor(request):
    notifications = Notification.objects.filter(is_read=False)
    return {'notifications': notifications}

def check_list_processor(request):
    products = CheckList.objects.filter(date=datetime.datetime.today())
    logger.info(products)
    return {'products': products}