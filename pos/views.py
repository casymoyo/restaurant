from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from inventory.models import Meal, Production, ProductionItems, Product, Logs
from loguru import logger
import json, datetime
from finance.models import Sale, SaleItem, CashBook
from settings.models import Printer
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpResponse
# from .tasks import print_receipt_task
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.utils import timezone
user = get_user_model()

@login_required
def pos(request):
    meals = Meal.objects.filter(deactivate=False)
    return render(request, 'pos.html', 
        {
            'meals':meals
        }
    )

@login_required
def product_meal_json(request):
    meals = Meal.objects.filter(deactivate=False).values('id', 'name', 'price')
    products = Product.objects.filter(raw_material=False).values('id', 'name', 'price', 'finished_product')

    combined_items = list(meals) + list(products)
    
    data = {
        'items': combined_items
    }
    
    return JsonResponse(data)

@login_required
def sales_list(request):
    today = datetime.datetime.today()
    sales = Sale.objects.filter(date=today)
    
    total_sales = sum(sale.total_amount for sale in sales) 
    
    sales_data = list(sales.values())
    data = {
        'sales': sales_data,
        'total_sales': total_sales
    }
    return JsonResponse(data)

@login_required
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

@login_required
@transaction.atomic
def process_sale(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data['items']
            staff = data['staff']
            
            logger.info(data)

            sub_total = sum(item['price'] * item['quantity'] for item in items)
            logger.info(sub_total)
            
            tax = sub_total * 0.15 # To be dynamically stipulated
            logger.info(tax)
            
            total_amount = sub_total + tax
            
            sale = Sale.objects.create(
                total_amount=total_amount,
                tax=tax,
                sub_total=sub_total,
                cashier=user.objects.get(id=1),
                staff=True if staff else False
            )
            
            today = timezone.now().date()
            for item in items:
                meal = get_object_or_404(Meal, id=item['meal_id'])
                if item['type'] == False:
                    
                    sale_item = SaleItem.objects.create(
                        sale=sale,
                        meal=meal,
                        quantity=item['quantity'],
                        price=meal.price
                    )
                    
                    for dish in meal.dish.all():
                        remaining_quantity = sale_item.quantity
                        production_items = ProductionItems.objects.filter(
                            production__date_created=today, dish=dish
                        ).order_by('production__time_created')  # Order by the time the production was created to follow FIFO

                        for pp_item in production_items:
                            if pp_item.portions == pp_item.portions_sold:
                                continue  
                            
                            available_portions = pp_item.portions - pp_item.portions_sold
                            
                            if remaining_quantity <= available_portions:
                                if staff:
                                    pp_item.staff_portions += remaining_quantity
                                    logger.info('staff')
                                else:
                                    pp_item.portions_sold += remaining_quantity
                                    logger.info('sale')
                                
                                pp_item.left_overs -= remaining_quantity
                                pp_item.save()
                                break  # Done processing this sale item
                            
                            else:
                                if staff:
                                    pp_item.staff_portions += available_portions
                                else:
                                    pp_item.portions_sold += available_portions

                                pp_item.left_overs -= available_portions
                                pp_item.save()
                                
                                remaining_quantity -= available_portions  # Move to the next batch
                        
                        if remaining_quantity > 0:
                            raise ValueError(f"Insufficient portions for dish {dish.name}.")
                            
                else:
                    product = get_object_or_404(Product, id=item['meal_id'])
                    product.quantity -= item['quantity']
                    
                    sale_item = SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=item['quantity'],
                        price=meal.price
                    )
                    
                    Logs.objects.create(
                        user=request.user, 
                        action='sale',
                        product=product,
                        quantity=sale_item.quantity,
                        total_quantity=product.quantity,
                    )
                    
                    product.save()
                    
                CashBook.objects.create(
                    sale=sale, 
                    amount=sale.total_amount,
                    debit=True,
                    description=f'Sale (Receipt number: {sale.receipt_number})'
                )
                    
            logger.info(f'Sale: {sale.id} Processed')
            return JsonResponse({'success': True, 'sale_id': sale.id}, status=201)

        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f'Error processing sale: {str(e)}')
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


