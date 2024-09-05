from django.test import TestCase
from django.urls import reverse
from users.models import User
from django.utils.timezone import localdate
from .models import (
    ProductionRawMaterials, 
    Production, 
    ProductionItems, 
    Meal, 
    Product, 
    Logs
)

from finance.models import (
    COGS,
    Sale, 
    SaleItem, 
    CashBook, 
)
import json

# to add product unit and category
class ProcessSaleTestCase(TestCase):
    def setUp(self):
        # Set up initial data for the test
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.kaolite_product = Product.objects.create(name='Kaolite', cost=10)
        self.salt_product = Product.objects.create(name='salt sachets', cost=5)
        
        self.kaolite = ProductionRawMaterials.objects.create(product=self.kaolite_product, quantity=100)
        self.salts = ProductionRawMaterials.objects.create(product=self.salt_product, quantity=100)
        
        self.meal = Meal.objects.create(name='Test Meal', price=100)
        self.production = Production.objects.create(date_created=localdate())
        self.production_item = ProductionItems.objects.create(
            production=self.production, dish=self.meal.dish.all(), portions=10, portions_sold=0, staff_portions=0, left_overs=10
        )
        self.cogs = COGS.objects.create(date=localdate(), amount=0)
        
    def test_process_sale_sitting_order(self):
        self.client.login(username='testuser', password='12345')
        data = {
            'items': [{'meal_id': self.meal.id, 'quantity': 1, 'price': 100, 'type': False}],
            'staff': False,
            'order_type': 'sitting'
        }
        response = self.client.post(reverse('process_sale'), json.dumps(data), content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Sale.objects.filter(cashier=self.user).exists())
        self.assertTrue(SaleItem.objects.filter(sale__cashier=self.user).exists())
        self.assertTrue(CashBook.objects.filter(sale__cashier=self.user).exists())
        self.assertEqual(ProductionRawMaterials.objects.get(product=self.salt_product).quantity, 99)
        self.assertEqual(COGS.objects.get(date=localdate()).amount, 5)
        
    def test_process_sale_takeaway_order(self):
        self.client.login(username='testuser', password='12345')
        data = {
            'items': [{'meal_id': self.meal.id, 'quantity': 1, 'price': 100, 'type': False}],
            'staff': False,
            'order_type': 'takeaway'
        }
        response = self.client.post(reverse('pos/process_sale'), json.dumps(data), content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Sale.objects.filter(cashier=self.user).exists())
        self.assertTrue(SaleItem.objects.filter(sale__cashier=self.user).exists())
        # self.assertTrue(CashBook.objects.filter(sale__cashier=self.user).exists())
        self.assertEqual(ProductionRawMaterials.objects.get(product=self.salt_product).quantity, 99)
        self.assertEqual(ProductionRawMaterials.objects.get(product=self.kaolite_product).quantity, 99)
        self.assertEqual(COGS.objects.get(date=localdate()).amount, 15)
        
    def test_process_sale_insufficient_stock(self):
        self.client.login(username='testuser', password='12345')
        self.kaolite.quantity = 0
        self.kaolite.save()
        
        data = {
            'items': [{'meal_id': self.meal.id, 'quantity': 1, 'price': 100, 'type': False}],
            'staff': False,
            'order_type': 'takeaway'
        }
        response = self.client.post(reverse('process_sale'), json.dumps(data), content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('Please refill the stocks for kaolites', response.json()['message'])
        
    def test_process_sale_invalid_meal(self):
        self.client.login(username='testuser', password='12345')
        
        data = {
            'items': [{'meal_id': 9999, 'quantity': 1, 'price': 100, 'type': False}],
            'staff': False,
            'order_type': 'sitting'
        }
        response = self.client.post(reverse('process_sale'), json.dumps(data), content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
