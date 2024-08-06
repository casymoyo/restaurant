from django.db import models
from inventory.models import Meal
from django.contrib.auth import get_user_model

User = get_user_model()

class Expense(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    debit = models.BooleanField(default=False)
    credit = models.BooleanField(default=False)
    
    def __str__(self) -> str:
        return f'{self.amount}'

class Sale(models.Model):
    cashier = models.ForeignKey(User, on_delete=models.CASCADE)
    total_amount= models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    date = models.DateField(auto_now_add=True)
    
    def __str__(self) -> str:
        return f'{self.meal} -> ({self.total_amount})'
    
class SaleItem(models.Model):
    sale = sale = models.ForeignKey(Sale, on_delete=models.CASCADE, null=True)
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE),
    quantity = models.IntegerField(),
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    time = models.TimeField(auto_now_add=True)
    
class CashBook(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, null=True)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    debit = models.BooleanField(default=False)
    credit = models.BooleanField(default=False)
    
    def __str__(self) -> str:
        return f'{self.amount}'
    