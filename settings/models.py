from django.db import models
from users.models import User

class Printer(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, null=True, blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name 
    
class Modules(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name
    
class NotificationEmails(models.Model):
    email = models.EmailField()
    module = models.ForeignKey(Modules, on_delete=models.CASCADE)
    
    def __str__(self):
        return f'{self.module}: ({self.email})'

class StockEvaluation(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name


class Permission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.CharField(max_length=100)  
    name = models.CharField(max_length=100)    
    is_allowed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.parent} - {self.name} : {'Allowed' if self.is_allowed else 'Not Allowed'}"