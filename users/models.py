from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    
    USER_ROLES = (
        ('admin', 'Admin'),
        ('chef', 'Chef'),
        ('sales', 'Salesperson'),
        ('accountant', 'Accountant')    
    )
    
    profile_image = models.ImageField(upload_to='Profile_images', blank=True, null=True)
    phonenumber = models.CharField(max_length=13)
    role = models.CharField(choices=USER_ROLES, max_length=50)
    
    def __str__(self) -> str:
        return self.username