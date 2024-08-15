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
            
            logger.info(staff)

            sub_total = sum(item['price'] * item['quantity'] for item in items)
            logger.info(sub_total)
            
            tax = sub_total * 0.15 #to be dynamically stipulated
            logger.info(tax)
            
            total_amount = sub_total 
            
            sale = Sale.objects.create(
                total_amount=total_amount,
                tax=tax,
                sub_total=sub_total,
                cashier=user.objects.get(id=1),
                staff= True if staff else False
            )
            
            latest_plan = Production.objects.latest('time_created')

            for item in items:
                if not item['type']:
                    meal = get_object_or_404(Meal, id=item['meal_id'])
                    
                    sale_item = SaleItem.objects.create(
                    sale=sale,
                    meal=meal,
                    quantity=item['quantity'],
                    price=meal.price
                )
                
                for dish in meal.dish.all():
                    try:
                        pp_item = ProductionItems.objects.get(production=latest_plan, dish=dish)
                        
                        if pp_item.portions == pp_item.portions_sold:
                            raise ValueError(f'Related dish ({pp_item.dish.name}) portions exhausted.')
                        
                        if staff:
                            pp_item.staff_portions += sale_item.quantity
                            logger.info('staff')
                        else:
                            pp_item.portions_sold += sale_item.quantity
                            logger.info('sale')
                            
                        pp_item.left_overs -= sale_item.quantity
                        pp_item.save()
                        
                    except ProductionItems.DoesNotExist:
                        logger.info(f'Production item not found for dish {dish.name}')
                        raise ValueError(f'Production item not found for dish {dish.name}')
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
                        action= 'sale',
                        product=product,
                        quantity=sale_item.quantity,
                        total_quantity=product.quantity,
                    )
                    
                    product.save()
                    
                CashBook.objects.create(
                    sale=sale, 
                    amount = sale.total_amount,
                    debit=True,
                    description=f'Sale (Receipt number: {sale.receipt_number})'
                )
                    
            logger.info(f'Sale: {sale.id} Processed')
            return JsonResponse({'success': True, 'sale_id': sale.id}, status=201)

        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f'Error processing sale: {str(e)}')
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


