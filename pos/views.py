from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from inventory.models import Meal, Production, ProductionItems, Product
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

def product_meal_json(request):
    meals = Meal.objects.filter(deactivate=False).values('id', 'name', 'price')
    products = Product.objects.filter(raw_material=False).values('id', 'name', 'price')
    logger.info(products )
    data = {
        'meals': list(meals),
        'products': list(products)
    }
    
    return JsonResponse(data)

def sales_list(request):
    today = datetime.datetime.today()
    sales = Sale.objects.filter(date=today)
    
    total_sales = sum(sale.total_amount for sale in sales) 
    
    sales_data = list(sales.values())
    data = {
        'sales': sales_data,
        'total_sales': total_sales
    }
    logger.info(data)
    return JsonResponse(data)

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

@transaction.atomic
def process_sale(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data['items']
            
            logger.info(items)

            sub_total = sum(item['price'] * item['quantity'] for item in items)
            logger.info(sub_total)
            
            tax = sub_total * 0.15 #to be dynamically stipulated
            logger.info(tax)
            
            total_amount = sub_total 
            
            sale = Sale.objects.create(
                total_amount=total_amount,
                tax=tax,
                sub_total=sub_total,
                cashier=user.objects.get(id=1)
            )
            
            latest_plan = Production.objects.latest('time_created')

            for item in items:
                meal = get_object_or_404(Meal, id=item['meal_id'])
                
                sale_item = SaleItem.objects.create(
                    sale=sale,
                    meal=meal,
                    quantity=item['quantity'],
                    price=meal.price
                )
                
                CashBook.objects.create(
                    sale=sale, 
                    amount = meal.price,
                    debit=True,
                    description=f'Sale (Receipt number: {sale.receipt_number})'
                )
                
                try:
                    for dish in meal.dish.all():
                        pp_item = ProductionItems.objects.get(production=latest_plan, dish=dish)
                        pp_item.portions -= sale_item.quantity
                        pp_item.save()
                
                    # print_receipt_view(request, sale.id)
                    generate_receipt_pdf(request)
                
                except ProductionItems.DoesNotExist:
                    logger.info(f'Production item not found for dish {dish.name}')
                    return JsonResponse({'success': False, 'message': f'Production item not found for dish {dish.name}'}, status=400)
                except Exception as e:
                    return JsonResponse({'success': False, 'message': str(e)}, status=400)
            logger.info(f'Sale: {sale.id} Processed')
            return JsonResponse({'success': True, 'sale_id': sale.id}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        
def print_receipt_view(request, sale_id):
    print_receipt_task.delay(sale_id)
    logger.info('printing_receipt')
    
def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="receipt.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    logger.info('done')
    return response

def generate_receipt_pdf(request):
    logger.info('here')
    context = {
        'item': 'Burger',
        'quantity': 1,
        'price': 1.00,
        'total': 1.00,
        'tax': 0.00,
        'cash': 1.00,
        'change': 0.00,
        'cashier': 'VIMBAINASHE M',
        'date': 'Thu 08 08, 2024 10:12',
        'transaction': '45512425105404',
        'till': 'Server',
        'sales_channel': 'USD',
        'total_qty': 1
    }
    return render_to_pdf('receipt_template.html', context)

