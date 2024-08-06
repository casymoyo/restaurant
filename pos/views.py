from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from inventory.models import MealDish, Meal
from loguru import logger
import json
from finance.models import Sale, SaleItem, CashBook
from django.contrib.auth import get_user_model

user = get_user_model()

def pos(request):
    meals = Meal.objects.all()
    logger.info(f'meals: {meals.values()}')
    return render(request, 'pos.html', 
        {
            'meals':meals
        }
    )

def meal_detail_json(request, meal_id):
    if request.method == 'POST':
        try:
            meal = Meal.objects.filter(id=meal_id)
            meal_data = {
                'id':meal.id,
                'name':meal.name,
                'price':meal.price
            }
        except Meal.DoesNotExist:
            return JsonResponse({'success':False, 'message':f'meal with ID: {meal_id} doesn\'t exists'})
        
        return JsonResponse({'success':True, 'data': meal_data})

def process_sale(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            received_amount = data['received_amount']
            items = data['items']

            sub_total = sum(item['price'] * item['quantity'] for item in items)
            logger.info(sub_total)
            tax = sub_total * 0.15 #to be dynamically stipulated
            logger.info(tax)
            total_amount = sub_total + tax
            logger.info(total_amount)
            sale = Sale.objects.create(
                total_amount=total_amount,
                tax=tax,
                sub_total=sub_total,
                cashier=user.objects.get(id=1)
            )

            for item in items:
                meal = get_object_or_404(Meal, id=item['meal_id'])
                
                sale_item = SaleItem.objects.create(
                    sale=sale,
                    meal=meal,
                    quantity=item['quantity'],
                    price=meal.price
                )
                
                CashBook.objects.create(
                    sale=sale_item, 
                    amount = meal.price,
                    debit=True
                )
            logger.info(f'Sale: Processed')
            return JsonResponse({'success': True, 'sale_id': sale.id}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        