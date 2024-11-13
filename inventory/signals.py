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

# @receiver(post_save, sender=Product)
# def check_stock_level(sender, instance, **kwargs):
#     logger.info('here')
#     logger.info(instance)
#     logger.info(f'quantity: {instance.quantity}, threshold: {instance.min_stock_level}')
#     if instance.quantity < instance.min_stock_level:
#         Notification.objects.create(
#             product=instance,
#             message=f"The stock level of {instance.name} is below the minimum threshold. {instance.quantity}."
#         )

#         subject = 'Stock Alert'
#         message = render_to_string('email/stock_alert.html', {
#             'product': instance,
#             'message': f"The stock level of {instance.name} is below the threshold."
#         })
#         send_mail(
#             subject,
#             message,
#             'admin@techcity.co.zw',  
#             ['cassymyo@gmail.com'],  
#             fail_silently=False,
#         )

#         channel_layer = get_channel_layer()
#         async_to_sync(channel_layer.group_send)(
#             f'user_{instance.name}',
#             {
#                 'type': 'send_notification',
#                 'message': f"The stock level of {instance.name} is below the minimum threshold."
#             }
#         )
#         logger.info('done')