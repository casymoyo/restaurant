from django.db import models

class Notification(models.Model):
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    alert_type = models.CharField(max_length=10, choices=(
        ('warning', 'warning'),
        ('danger', 'danger')
    ), null=True)