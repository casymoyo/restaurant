# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.core.mail import send_mail
from .models import Product
from .models import Notification  
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from loguru import logger
from .tasks import send_email_task
from users.models import User

@receiver(post_save, sender=Product)
def check_stock_level(sender, instance, **kwargs):
    subject = ''
    message = ''

    if instance.quantity <= instance.min_stock_level and instance.quantity > 0:
        notification = Notification.objects.create(
            description=f"The stock level of {instance.name} is below the minimum threshold. {instance.quantity}.",
            alert_type='warning'
        )

        subject = 'Low Stock Alert'
        message = f'{instance.name} has now reached its minimum threshold'
    elif instance.quantity == 0:
        notification = Notification.objects.create(
            description=f"The stock level of {instance.name} is below the minimum threshold. {instance.quantity}.",
            alert_type='danger'
        )
      
        subject = 'Out Of stock Alert'
        message = f'{instance.name} is now out of stock'

    # send email notification
    recipient_list = [r['email'] for r in User.objects.all().values()]
    send_email_task.delay(subject, message, recipient_list)

    # live notification update
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "notifications",
        {
            'type': 'send_notification',
            'message': f'{notification.timestamp}: {notification.description}'
        }
    )


        

@receiver(post_save, sender=Notification)
def notification_websocket(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "notifications",
        {
            'type': 'send_notification',
            'message': {
                'alert_type': 'cool',
                'message':f'{instance.timestamp}: {instance.description}'
            }
        }
    )

    