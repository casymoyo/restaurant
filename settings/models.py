from django.db import models

class Printer(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, null=True, blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
class NotificationEmails(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    
    def __str__(self):
        return f'{self.name}: ({self.email})'


