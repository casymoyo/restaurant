import uuid
import datetime
from django.db import models
from users.models import User
from django.db.models import F

class Category(models.Model):
    name = models.CharField(max_length=255)
    
    def __str__(self):
        return self.name

class UnitOfMeasurement(models.Model):
    unit_name = models.CharField(max_length=255)
    
    def __str__(self) -> str:
        return self.unit_name

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()

    def __str__(self):
        return self.name
    
class Meal(models.Model):
    name = models.CharField(max_length=255)
    # to but the dishes which makes the meal
    
    def __str__(self) -> str:
        return self.name

class Product(models.Model):
    
    tax_choices = [
        ('exempted', 'Exempted'),
        ('standard', 'Standard'),
        ('zero rated', 'Zero Rated')
    ]
    
    name = models.CharField(max_length=255)
    quantity = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=1) 
    unit = models.ForeignKey(UnitOfMeasurement, on_delete=models.CASCADE, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    tax_type = models.CharField(max_length=50, choices=tax_choices)
    min_stock_level = models.IntegerField(default=0, null=True)
    portion_multiplier = models.FloatField(default=1, null=True, blank=True)
    raw_material = models.BooleanField(default=False)
    finished_product = models.BooleanField(default=False)
    description = models.TextField()
    deactivate = models.BooleanField(default=False)
    
    
    def __str__(self) -> str:
        return self.name

class Production(models.Model):
    date_created = models.DateField(auto_now_add=True)
    status = models.BooleanField(default=False)
    production_plan_number = models.CharField(max_length=10, unique=True, default='')

    def save(self, *args, **kwargs):
        if not self.production_plan_number:
            self.production_plan_number = self.generate_production_plan_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_production_plan_number():
        return f'PP-{uuid.uuid4().hex[:5].upper()}'

    def __str__(self) -> str:
        return self.production_plan_number

    
class ProductionItems(models.Model):
    production = models.ForeignKey(Production, on_delete=models.CASCADE)
    raw_material = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.FloatField()
    dish = models.ForeignKey('inventory.dish', on_delete=models.CASCADE)
    rm_carried_forward_quantity = models.IntegerField()
    lf_carried_forward_quantity = models.IntegerField()
    actual_quantity = models.IntegerField()
    production_completion_time = models.TimeField(null=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self) -> str:
        return f'{self.raw_material} ({self.quantity})'

class Dish(models.Model):
    name = models.CharField(max_length=100)
    raw_material =  models.ForeignKey(Product, on_delete=models.CASCADE)
    
    def __str__(self) -> str:
        return self.name
    
class DeclaredRawMaterial(models.Model):
    raw_material = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.FloatField()
    date = models.DateField(auto_now_add=True)
    
    def __str__(self) -> str:
        return f'{self.raw_material} ({self.quantity})'

class DeclaredWastageMeal(models.Model):
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    portion = models.IntegerField()
    date = models.DateField(auto_now_add=True)
    
    def __str__(self) -> str:
        return f'{self.meal} ({self.date})'

class DeclaredLeftOverDish(models.Model):
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE)
    portion = models.IntegerField()
    date = models.DateField(auto_now_add=True)
    
    def __str__(self) -> str:
        return f'{self.dish} ({self.date})'

class SalePortion(models.Model):
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    portion = models.IntegerField()
    date = models.DateField(auto_now_add=True)
    
    def __str__(self) -> str:
        return f'{self.meal} ({self.date})'
    

# class today(models.Model):
#     production = models.ForeignKey(Production, on_delete=models.CASCADE)
#     declared_raw_material = models.ForeignKey(DeclaredRawMaterial, on_delete=models.CASCADE)
#     declared_wastage = models.ForeignKey(DeclaredWastageMeal, on_delete=models.CASCADE)
#     declared_sale = models.ForeignKey(SalePortion, on_delete=models.CASCADE)
    
#     def __str__(self) -> str:
#         return 


class PurchaseOrder(models.Model):
    """Model for purchase orders."""

    status_choices = [
        ('pending', 'Pending'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('canceled', 'Canceled')
    ]

    order_number = models.CharField(max_length=100, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    order_date = models.DateTimeField(default=datetime.datetime.today())
    delivery_date = models.DateField(null=True, blank=True)
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, choices=status_choices, default='pending')
    notes = models.TextField(null=True, blank=True)
    discount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    handling_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    other_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    is_partial = models.BooleanField(default=False)  
    received = models.BooleanField(default=False)

    def generate_order_number():
        return f'PO-{uuid.uuid4().hex[:10].upper()}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super(PurchaseOrder, self).save(*args, **kwargs)

    def check_partial_status(self):
        partial_items = self.items.filter(received_quantity__lt=F('quantity'))
        self.is_partial = partial_items.exists()
        self.save()

    def __str__(self):
        return f"PO {self.order_number} - {self.supplier}"

class PurchaseOrderItem(models.Model):

    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    received_quantity = models.IntegerField(default=0) 
    received = models.BooleanField(default=False, null=True)

    def receive_items(self, quantity):
       
        self.received_quantity += quantity
        if self.received_quantity >= self.quantity:
            self.received = True
        self.save()
        self.purchase_order.check_partial_status()  

    def check_received(self):
        """
        Checks if all related items in the purchase order with the same order_number are received and updates the purchase order's "received" flag.
        """
        order_number = self.purchase_order.order_number
        purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order__order_number=order_number)

        all_received = True
        for item in purchase_order_items:
            if not item.received:
                all_received = False
            break

        purchase_order = PurchaseOrder.objects.get(order_number=order_number)
        purchase_order.received = all_received
        purchase_order.save()

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

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
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    purchase_order = models.ForeignKey(PurchaseOrder, null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.IntegerField()
    total_quantity = models.IntegerField()
    timestamp = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255, null=True)
    



    

    
