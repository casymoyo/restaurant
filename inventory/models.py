import uuid
import datetime
from django.db import models
# from users.models import User
from django.db.models import F
from django.forms import modelformset_factory

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
    
    
    def __str__(self) -> str:
        return self.name

class Product(models.Model):
    
    tax_choices = [
        ('exempted', 'Exempted'),
        ('standard', 'Standard'),
        ('zero rated', 'Zero Rated')
    ]
    
    name = models.CharField(max_length=255)
    quantity = models.FloatField()
    cost = models.DecimalField(max_digits=10, decimal_places=4)
    price = models.DecimalField(max_digits=10, decimal_places=3, default=1) 
    unit = models.ForeignKey(UnitOfMeasurement, on_delete=models.CASCADE, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)
    tax_type = models.CharField(max_length=50, choices=tax_choices, null=True)
    min_stock_level = models.FloatField(default=0, null=True)
    raw_material = models.BooleanField(default=False)
    finished_product = models.BooleanField(default=False)
    description = models.TextField()
    deactivate = models.BooleanField(default=False)
    
    def __str__(self) -> str:
        return self.name
class ProductionRawMaterials(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.FloatField()
    
    def __str__(self) -> str:
        return self.product.name

class Production(models.Model):
    date_created = models.DateField(auto_now_add=True)
    time_created = models.TimeField(auto_now_add=True)
    status = models.BooleanField(default=False)
    production_plan_number = models.CharField(max_length=10, unique=True, default='')
    declared = models.BooleanField(default=False)
    
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
    dish = models.ForeignKey('inventory.dish', on_delete=models.CASCADE)
    lf_brought_forward_quantity = models.FloatField(null=True, blank=True)
    actual_quantity = models.FloatField(null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remaining_raw_material = models.FloatField(default=0, null=True, blank=True)
    declared = models.BooleanField(default=False)
    left_overs = models.FloatField(default=0, null=True, blank=True)
    wastage = models.FloatField(default=0, null=True, blank=True)      
    portions = models.FloatField(default=0, null=True)
    staff_portions = models.FloatField(default=0, null=True)  
    declared_quantity = models.FloatField(default=0, null=True)
    portions_sold = models.FloatField(default=0, null=True)
    allocated = models.BooleanField(default=False)

class MinorProductionItems(models.Model):
    production = models.ForeignKey(Production, on_delete=models.CASCADE)
    minor_raw_material = models.ForeignKey(Product, on_delete=models.CASCADE)
    total_quantity_per_kg = models.FloatField()
    planned_quantity = models.FloatField()
    expected_quantity = models.FloatField()
    actual_quantity = models.FloatField(null=True)
    cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=1) 
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=1) 
    
    def __str__(self) -> str:
        return f'{self.minor_raw_material}'


class AllocatedRawMaterials(models.Model):
    production = models.ForeignKey(Production, on_delete=models.CASCADE)
    raw_material = models.ForeignKey(Product, on_delete=models.CASCADE)
    remaining_quantity = models.FloatField(null=True)
    quantity = models.FloatField()
    
    def __str__(self) -> str:
        return f'{self.production} ({self.raw_material}: ({self.quantity}))'
    
class ProductionInventory(models.Model):
    raw_material = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.FloatField()
    
    def __str__(self) -> str:
        return f'{self.raw_material}: ({self.quantity})'


class Dish(models.Model):
    name = models.CharField(max_length=100)
    portion_multiplier = models.FloatField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    category = models.CharField(choices=[
        ('Fast food', 'Fast food'),
        ('Meat', 'Meat'),
        ('Starch', 'Starch'),
        ('Salad', 'Salad')
    ])
    dish = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name

class Ingredient(models.Model):
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, null=True)
    note = models.CharField(max_length=100, null=True)
    quantity = models.FloatField()
    raw_material = models.ForeignKey(Product, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.raw_material.name          
    
class MealCategory(models.Model):
    name = models.CharField(max_length=255)
    
    def __str__(self) -> str:
        return self.name
    
class Meal(models.Model):
    name = models.CharField(max_length=255)
    price = models.CharField(max_length=255)
    dish = models.ManyToManyField(Dish, related_name='dishes')
    category = models.ForeignKey(MealCategory, on_delete=models.CASCADE, null=True)
    deactivate = models.BooleanField(default=False)
    meal = models.BooleanField(default=True)
    
    def __str__(self) -> str:
        return self.name

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
    order_date = models.DateTimeField(auto_now_add=True)
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
    quantity = models.FloatField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    received_quantity = models.FloatField(default=0) 
    received = models.BooleanField(default=False, null=True)
    note = models.CharField(default='', null=True, max_length=255)

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
    sale = models.ForeignKey('finance.sale', on_delete=models.CASCADE, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    purchase_order = models.ForeignKey(PurchaseOrder, null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.FloatField()
    total_quantity = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, null=True)
    
class MinorRawMaterials(models.Model):
    raw_material = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.FloatField()
    quantity_left = models.FloatField()
    
    def __str__(self) -> str:
        return self.raw_material.name
    

class EndOfDay(models.Model):
    date = models.DateField(auto_now_add=True)
    done = models.BooleanField(default=False)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    cashed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    def __str__(self) -> str:
        return f'{self.total_sales}'
    
class EndOfDayItems(models.Model):
    end_of_day = models.ForeignKey(EndOfDay, on_delete=models.CASCADE)
    dish_name = models.CharField(max_length=50)
    total_portions = models.IntegerField()
    total_sold = models.IntegerField()
    staff_portions = models.IntegerField()
    wastage = models.FloatField()
    leftovers = models.FloatField()
    expected = models.FloatField()
    
    def __str__(self) -> str:
        return f'{self.end_of_day.date}: {self.dish_name}'
    
class Reorder(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    ordered = models.BooleanField(default=False)
    approx_days = models.FloatField()
    reorder_quantity = models.FloatField()

    def __str__(self) -> str:
        return f'{self.product.name}'
    
class Transfer(models.Model):
    transfer_number = models.CharField(max_length=20, unique=True)
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.transfer_number:
            self.transfer_number = self.get_next_transfer_number()
        super().save(*args, **kwargs)

    def get_next_transfer_number(self):
        last_transfer = Transfer.objects.all().order_by('created_at').last()
        if last_transfer:
            last_number = int(last_transfer.transfer_number.lstrip('0'))
            next_number = last_number + 1
        else:
            next_number = 1
        return f'{next_number:05}'

    def __str__(self):
        return self.transfer_number

class TransferItems(models.Model):
    transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.FloatField()

    def __str__(self):
        return f'{self.quantity} of {self.product.name}'


class ProductionLogs(models.Model):
    
    ACTION_CHOICES = [
        ('sale', 'sale'),
        ('stock in', 'stock in'),
        ('declared', 'declared'),
        ('to production', 'to production'),
    ]
    
    product = models.ForeignKey(ProductionRawMaterials, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    quantity = models.FloatField()
    total_quantity = models.FloatField()
    timestamp = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255, null=True)   


class Notification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    production = models.ForeignKey(Production, on_delete=models.CASCADE, null=True)
    expense = models.ForeignKey('finance.Expense', on_delete=models.CASCADE, null=True)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

class CheckList(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    date = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return self.product.name
    

    