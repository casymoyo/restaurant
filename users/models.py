from django.db import models
from django.contrib.auth.models import AbstractUser

class Company(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    

    def __str__(self) -> str:
        return self.name

class User(AbstractUser):
    
    USER_ROLES = (
        ('admin', 'Admin'),
        ('chef', 'Chef'),
        ('sales', 'Salesperson'),
        ('accountant', 'Accountant')    
    )
    
    phonenumber = models.CharField(max_length=13)
    role = models.CharField(choices=USER_ROLES, max_length=50)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="users")

    def __str__(self) -> str:
        return self.username
