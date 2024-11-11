from celery import shared_task
from django.core.mail import send_mail
from users.models import User
from loguru import logger

@shared_task
def send_email_task(subject, message, recipient_list):
    send_mail(
        subject,
        message,
        'admin@techcity.co.zw', 
        recipient_list,
        fail_silently=False,
    )
    logger.info(f'{subject}: email sent')