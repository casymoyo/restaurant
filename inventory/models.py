import uuid
import datetime
from django.db import models
from users.models import User

class FinishedGoodsCategory(models.Model):
    name = models.CharField(max_length=255)
    
    def __str__(self):
        return self.name

class UnitOfMeasurement(models.Model):
    name = models.CharField(max_length=255)
    
    def __str__(self) -> str:
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()

    def __str__(self):
        return self.name

class RawMaterials(models.Model):
    name = models.CharField(max_length=255)
    quantity = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.ForeignKey(UnitOfMeasurement, on_delete=models.CASCADE)
    portion_multiplier = models.FloatField(default=1)
    description = models.TextField()
    deactivate = models.BooleanField(default=False)
    
    def __str__(self) -> str:
        return self.name

class FinishedProduct(models.Model):
    name = models.CharField(max_length=255)
    quantity = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(FinishedGoodsCategory, on_delete=models.CASCADE)
    price =models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self) -> str:
        return self.name


class Production(models.Model):
    date_created = models.DateField(auto_now_add=True)
    status = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.date_created

class ProductionItems(models.Model):
    raw_material = models.ForeignKey(RawMaterials, on_delete=models.SET_NULL, null=True)
    quantity = models.FloatField()
    raw_material = models.ForeignKey(RawMaterials, on_delete=models.SET_NULL, null=True)
    sold_quantity = models.IntegerField(null=True)
    wastage = models.IntegerField(null=True)
    left_overs = models.IntegerField(null=True)
    variance = models.IntegerField(null=True)
        
    def __str__(self) -> str:
        return f'{self.raw_material} ({self.quantity})'


class PurchaseOrder(models.Model):

    status_choices = [
        ('pending', 'Pending'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('canceled', 'Canceled')
    ]

    order_number = models.CharField(max_length=100, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    order_date = models.DateTimeField(default=datetime.datetime.today())
    delivery_date = models.DateTimeField(null=True, blank=True)
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, choices=status_choices, default='pending')
    notes = models.TextField(null=True, blank=True)
    
    def generate_order_number(self):
        return f'PO-{uuid.uuid4().hex[:10].upper()}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super(PurchaseOrder, self).save(*args, **kwargs)

    def __str__(self):
        return f"PO {self.order_number} - {self.supplier}"

class PurchaseOrderItem(models.Model):

    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    raw_material = models.ForeignKey(RawMaterials, on_delete=models.SET_NULL, null=True)
    product = models.ForeignKey(FinishedProduct, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        # Calculate the total cost for the purchase order item
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
        # Update the total cost of the purchase order
        self.purchase_order.update_total_cost()

class Logs(models.Model):
    
    ACTION_CHOICES = [
        ('stock in', 'stock in'),
        ('Stock update', 'Stock update'),
        ('edit', 'Edit'),
        ('sale', 'Sale'), 
        ('declined', 'Declined'),
        ('write off', 'write off'),
        ('defective', 'defective'),
        ('activated', 'activated'),
        ('deactivated', 'deactivated'),
        ('removed', 'removed')
    ]
    
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    quantity = models.IntegerField()
    total_quantity = models.IntegerField()
    timestamp = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255, null=True)



    

    
