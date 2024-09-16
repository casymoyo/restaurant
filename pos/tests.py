from django.test import TestCase
from django.urls import reverse
from users.models import User
from django.utils.timezone import localdate
from django.contrib.auth.models import User
from django.test import Client

from finance.models import (
    Sale, 
    SaleItem, 
    COGS, 
    Meal, 
    Product, 
    CashBook
)

from inventory.models import (
    Logs,
    Production, 
    ProductionItems, 
    ProductionRawMaterials, 
)

import json

class ProcessSaleTestCase(TestCase):
    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(username='testuser', password='password')
        
        # Create some products and production raw materials
        self.kaolite = ProductionRawMaterials.objects.create(product_name="Kaolite", quantity=50)
        self.salts = ProductionRawMaterials.objects.create(product_name="salt sachets", quantity=50)
        
        # Create a meal
        self.meal = Meal.objects.create(name='Chicken Meal', price=10.00)
        
        # Create production and production items for the meal
        self.production = Production.objects.create(date_created=localdate(), time_created='08:00')
        self.pp_item = ProductionItems.objects.create(production=self.production, dish=self.meal, portions=10, portions_sold=0)
        
        # Create COGS for today
        self.cogs = COGS.objects.create(date=localdate(), amount=0)
        
        self.client = Client()

    def authenticate_user(self):
        self.client.login(username='testuser', password='password')

    def test_process_sale_success(self):
        self.authenticate_user()

        data = {
            "items": [
                {
                    "meal_id": self.meal.id,
                    "quantity": 2,
                    "price": 10.00,
                    "type": False
                }
            ],
            "staff": None,
            "order_type": "sitting",
            "received_amount": 20.00
        }

        response = self.client.post(reverse('process_sale'), json.dumps(data), content_type="application/json")
        
        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        
        sale = Sale.objects.get(id=response_data['sale_id'])
        
        # Assert that a sale was created
        self.assertIsNotNone(sale)
        
        # Assert sale item was created
        sale_item = SaleItem.objects.get(sale=sale, meal=self.meal)
        self.assertEqual(sale_item.quantity, 2)
        
        # Assert stock levels were updated
        self.salts.refresh_from_db()
        self.assertEqual(self.salts.quantity, 48)

    def test_process_sale_insufficient_stock(self):
        self.authenticate_user()

        # Set Kaolite stock to 0
        self.kaolite.quantity = 0
        self.kaolite.save()

        data = {
            "items": [
                {
                    "meal_id": self.meal.id,
                    "quantity": 2,
                    "price": 10.00,
                    "type": False
                }
            ],
            "staff": None,
            "order_type": "takeaway",
            "received_amount": 20.00
        }

        response = self.client.post(reverse('process_sale'), json.dumps(data), content_type="application/json")

        # Assert failure due to insufficient Kaolite stock
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['message'], 'Please refill the stocks for kaolites')

    
    def test_process_sale_production_exhausted(self):
        self.authenticate_user()

        # Simulate the portions being sold out
        self.pp_item.portions_sold = 10
        self.pp_item.save()

        data = {
            "items": [
                {
                    "meal_id": self.meal.id,
                    "quantity": 2,
                    "price": 10.00,
                    "type": False
                }
            ],
            "staff": None,
            "order_type": "sitting",
            "received_amount": 20.00
        }

        response = self.client.post(reverse('process_sale'), json.dumps(data), content_type="application/json")

        # Sale should still succeed, but portions sold should be updated only for available production
        self.assertEqual(response.status_code, 201)
        response_data = response.json()

        sale = Sale.objects.get(id=response_data['sale_id'])
        
        # Assert that sale was created
        self.assertIsNotNone(sale)

        # Since the production plan was exhausted, we expect no update to this production item
        self.pp_item.refresh_from_db()
        self.assertEqual(self.pp_item.portions_sold, 10)

    
    def test_process_sale_for_staff(self):
        self.authenticate_user()

        data = {
            "items": [
                {
                    "meal_id": self.meal.id,
                    "quantity": 1,
                    "price": 10.00,
                    "type": False
                }
            ],
            "staff": "staff_member_id",  # Simulate a staff sale
            "order_type": "takeaway",
            "received_amount": None
        }

        response = self.client.post(reverse('process_sale'), json.dumps(data), content_type="application/json")

        self.assertEqual(response.status_code, 201)
        response_data = response.json()

        sale = Sale.objects.get(id=response_data['sale_id'])

        # Assert that received_amount matches the total amount for staff sales
        self.assertEqual(sale.total_amount, 10.00)




