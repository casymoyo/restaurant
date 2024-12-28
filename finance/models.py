from django.db import models
from inventory.models import Meal, Product, Dish
from django.contrib.auth import get_user_model

User = get_user_model()

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=255)
    
    def __str__(self) -> str:
        return self.name

class COGS(models.Model):
    date = models.DateField(auto_now_add=True)
    production = models.ForeignKey('inventory.production', on_delete=models.CASCADE, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    
class Expense(models.Model):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    date = models.DateField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    cancel = models.BooleanField(default=False)
    status = models.BooleanField(default=False)
    
    def __str__(self) -> str:
        return f'{self.amount}'

class Sale(models.Model):
    cashier = models.ForeignKey(User, on_delete=models.CASCADE)
    total_amount= models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    date = models.DateField(auto_now_add=True)
    receipt_number = models.CharField(max_length=10, blank=True)
    staff = models.BooleanField(default=False)
    change = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    void = models.BooleanField(default=False)

    
    def __str__(self) -> str:
        return f'{self.cashier} -> ({self.total_amount})'
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            last_receipt = Sale.objects.all().order_by('id').last()
            if last_receipt:
                last_receipt_number = int(last_receipt.receipt_number)
                new_receipt_number = '{:04d}'.format(last_receipt_number + 1)
            else:
                new_receipt_number = '0001'
            self.receipt_number = new_receipt_number
        super(Sale, self).save(*args, **kwargs)
    
class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    time = models.TimeField(auto_now_add=True)
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, null=True)
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    quantity = models.IntegerField()
    
class CashBook(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, null=True)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    debit = models.BooleanField(default=False, null=True)
    credit = models.BooleanField(default=False, null=True)
    description = models.CharField(max_length=255, default='')
    date = models.DateField(auto_now_add=True)
    manager = models.BooleanField(default=False)
    accountant = models.BooleanField(default=False, null=True)
    director = models.BooleanField(default=False, null=True)
    note = models.TextField(default='', null=True)
    cancelled = models.BooleanField(default=False, null=True)
    
    def __str__(self) -> str:
        return f'{self.amount}'
    
class CashBookNote(models.Model):
    entry = models.ForeignKey(CashBook, related_name="notes", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note by {self.user.username} on {self.timestamp}"
    
class transactionLog(models.Model):
    action_choice = [
        ('sale', 'sale'),
        ('expense', 'expense'),
        
    ]
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, null=True)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, null=True)
    action = models.CharField(max_length=10, choices=action_choice)
    
    
class CashUp(models.Model):
    cashier = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cashier')
    cashed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    sales = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    date = models.DateField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    
    def __str__(self) -> str:
        return f'{self.date}'
    
class CashierAccount(models.Model):
    cashier = models.ForeignKey(User, on_delete=models.CASCADE)
    cash_up = models.ForeignKey(CashUp, on_delete=models.CASCADE, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    status = models.BooleanField(default=False)
    
    def __str__(self) -> str:
        return f'{self.cashier.first_name} ({self.amount})'

class CashierPayments(models.Model):
    date = models.DateTimeField(auto_now_add=True, null=True)
    cashier = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self) -> str:
        return f'{self.cashier.cashier.first_name} ({self.amount})'
     
class EmailNotifications(models.Model):
    expense_notification = models.BooleanField(default=True)
    
class Change(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='sale_change')
    name = models.CharField(max_length=100)
    phonenumber = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    receipt_number = models.CharField(max_length=100)
    collected = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    cashier = models.ForeignKey(User, on_delete=models.CASCADE)
    claimed = models.BooleanField(default=False)
    
    def __str__(self) -> str:
        return f'{self.cashier.username} ({self.amount})'
    
class CashierExpense(models.Model):
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cashier = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255)
    status = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f'{self.name} ({self.amount})'

