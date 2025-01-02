import csv
import asyncio
import tempfile
import subprocess
import json, datetime
from loguru import logger
from decimal import Decimal
from datetime import timedelta
from django.db.models import Sum
from finance.models import Change, Sale, SaleItem
from django.db import transaction
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from finance.forms import ChangeForm
from asgiref.sync import sync_to_async
from django.utils.timezone import localdate
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from finance.models import Sale, SaleItem, CashBook, CashierExpense
from django.contrib.auth.decorators import login_required
from inventory.models import ProductionRawMaterials, ProductionLogs
from inventory.models import Meal, Production, ProductionItems, Product, Logs, Dish
from permisions.permisions import (
    admin_required,
    sales_required
)
from django.views.decorators.cache import cache_page
import requests
import tempfile
import logging
from django.db.models import Q
from django.contrib.auth import authenticate 
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


# logger = logging.getLogger('restaurant')  

# @cache_page(60*50)
@login_required
def pos(request):
    return render(request, 'pos.html')

@login_required
def product_meal_json(request):
    if request.method == 'GET':
        
        meals = Meal.objects.filter(deactivate=False)
        products = Product.objects.filter(raw_material=False).values('id', 'name', 'price', 'finished_product',)
        dishes = Dish.objects.all().values('id', 'name', 'price', 'dish')

        meal_data = [
            {
                'name':meal.name,
                'price':meal.price,
                'category':meal.category.name,
                'meal':meal.meal,
                'id':f'm-{meal.id}'
            }
            for meal in meals
        ]

        combined_items = meal_data + list(products) + list(dishes)
        
        data = {
            'items': combined_items
        }
    
        return JsonResponse(data)
    
    return JsonResponse('Invalid requesnt', status=500)

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
    

def create_client_change(client_data, receipt_number, cashier, sale):
    logger.info(f'client name: {client_data}')

    Change.objects.create(
        sale=sale,
        name=client_data.get('name'),
        phonenumber=client_data.get('phonenumber'),
        receipt_number=receipt_number,
        amount=client_data.get('balance'),
        collected=False,
        claimed=False,
        cashier=cashier
    )

@login_required
def process_sale(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            logger.info(f'Sales data {data}')


            items = data['items']
            staff = data['staff']
            change_data = data.get('change_data')
            order_type = data['order_type']
            received_amount = data.get('received_amount')
            meal_bool = data.get('meal')

            logger.info(items)

            logger.info('here ---------------------------------------------------------------------')

            sub_total = sum(item['price'] * item['quantity'] for item in items)
            
            tax = sub_total * 0.15 
            
            total_amount = sub_total

            balance=0
            if change_data:
                change_data = change_data[0]
                balance = change_data['balance']
            
            if staff:
                received_amount = 0.00

            with transaction.atomic():
                product = None

                if staff:
                    sale = Sale.objects.create(
                        total_amount=0.00,
                        tax=0.00,
                        sub_total=sub_total,
                        cashier=request.user,
                        staff=True,
                        change=0.00,
                        amount_paid=received_amount
                    )
                else:
                    sale = Sale.objects.create(
                        total_amount=total_amount,
                        tax=tax,
                        sub_total=sub_total,
                        cashier=request.user,
                        staff=False,
                        change=balance,
                        amount_paid=received_amount
                    )

                logger.info(sale)

                today = localdate()

                daily_productions = Production.objects.filter(date_created=today).order_by('time_created')

                logger.info(f'daily productions: {daily_productions}')
                
                for item in items:
                    if not item['type']:

                        logger.info('Processing meal or dish')
                        
                        meal = None
                        dish = None

                        logger.info(f'Looking for meal with id {item['meal_id']} or dishes with id {item['meal_id']}')

                        if item.get('meal'): 
                            meal_id = item['meal_id'].split('-')[1]

                            meal = get_object_or_404(Meal, id=meal_id)
                            logger.info(f'Sale for meal: {meal}')
                        elif item.get('dish'):  
                            dish = get_object_or_404(Dish, id=item['meal_id'])
                            logger.info(f'Sale for dish: {dish}')
                        else:
                            raise ValueError('Invalid item type: Neither meal nor dish specified.')
                        

                        if staff:
                            sale_item = SaleItem.objects.create(
                                sale=sale,
                                quantity=item['quantity'],
                                price=0.00
                            )
                        else:
                             sale_item = SaleItem.objects.create(
                                sale=sale,
                                quantity=item['quantity'],
                                price=meal.price if meal else dish.price,
                            )

                        if meal:
                            
                            sale_item.meal=meal

                        elif dish:

                            sale_item.dish=dish
                        
                        sale_item.save()

                        logger.info(f'Sale item saved: {sale_item}')
                        
                        def log(products, sale_item):
                            for product in products:
                                ProductionLogs.objects.create(
                                    user=request.user, 
                                    action='sale',
                                    product=product,
                                    quantity=sale_item.quantity,
                                    total_quantity=product.quantity,
                                )
                                logger.info(f'Log for {sale_item}')
                            
                    else:
                        logger.info('Finished goods')
                        product = get_object_or_404(Product, id=item['meal_id'])
                        product.quantity -= item['quantity']

                        logger.info(f'finished product {product}')
                        
                        if staff:
                            sale_item = SaleItem.objects.create(
                                sale=sale,
                                product=product,
                                quantity=item['quantity'],
                                price=0.00,
                            )
                        else:
                            sale_item = SaleItem.objects.create(
                                sale=sale,
                                product=product,
                                quantity=item['quantity'],
                                price=product.price,
                            )

                        logger.info(f'Saved sale item: {sale_item}')
                        
                        Logs.objects.create(
                            user=request.user, 
                            action='sale',
                            product=product,
                            quantity=sale_item.quantity,
                            total_quantity=product.quantity,
                        )

                        logger.info(f'log sale item: {sale_item}')

                        product.save()
                        logger.info(f'Saved product: {sale_item}')

                CashBook.objects.create(
                    sale=sale, 
                    amount=sale.total_amount,
                    debit=True,
                    description=f'Sale (Receipt number: {sale.receipt_number})'
                )

                logger.info('Cash book object created.')

                # create change
                if change_data:
                    logger.info(f'creating change object if change data exists')
                    
                    create_client_change(change_data, sale.receipt_number, sale.cashier, sale)

                Logs.objects.create(
                    user=request.user, 
                    action='sale',
                    sale=sale,
                    quantity=sale_item.quantity,
                    total_quantity=sale_item.quantity,
                )
                
                logger.info(f'Sale: {sale.id} Processed')

                data = {
                    'receipt_number': sale.receipt_number,
                    'date': str(localdate()),
                    'time': timezone.localtime().strftime("%H:%M:%S"),
                    'cashier': f'{request.user.first_name} {request.user.last_name}',
                    'receipt_number': sale.receipt_number,
                    'total_amount': sale.total_amount,
                    'receipt_number':sale.receipt_number,
                    'tax': sale.tax,
                    'sub_total': sale.sub_total,
                    'received_amount': received_amount,
                    'change': received_amount - sale.total_amount,
                    'items': list(SaleItem.objects.filter(sale=sale).values('quantity', 'price', 'meal__name', 'dish__name', 'product__name'))
                }

                # total_sales = Sale.objects.filter(date=today).aggregate(total=Sum('total_amount'))['total'] or 0
                # channel_layer = get_channel_layer()
                # async_to_sync(channel_layer.group_send)(
                #     "sales_group",
                #     {
                #         "type": "send_sales_update",
                #         "data": {"total_sales": str(total_sales)},
                #     }
                # )
                return JsonResponse({'success': True, 'data': data}, status=201)
        except Exception as e:
            logger.error(f'Error processing sale: {str(e)}')
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=405)

@login_required
def change_list(request):
    filter_option = request.GET.get('filter', 'today')
    now = datetime.datetime.now()
    end_date = now
    
    if filter_option == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'this_week':
        start_date = now - timedelta(days=now.weekday())
    elif filter_option == 'yesterday':
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'this_month':
        start_date = now.replace(day=1)
    elif filter_option == 'last_month':
        start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    elif filter_option == 'this_year':
        start_date = now.replace(month=1, day=1)
    elif filter_option == 'custom':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        start_date = now - timedelta(days=now.weekday())
        end_date = now
        
    changes = Change.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date).order_by('timestamp')
    total_change_amount = changes.filter(collected=False).aggregate(total=Sum('amount'))['total'] or 0
    
    return render(request, 'finance/change_list.html', 
        {
            'filter_option': filter_option,
            'changes':changes,
            'end_date':end_date,
            'start_date':start_date,
            'total':total_change_amount
        }
    )

@login_required
def download_change_report(request):
    filter_option = request.GET.get('filter', 'this_week')
    now = datetime.now()
    end_date = now
    
    if filter_option == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'this_week':
        start_date = now - timedelta(days=now.weekday())
    elif filter_option == 'yesterday':
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'this_month':
        start_date = now.replace(day=1)
    elif filter_option == 'last_month':
        start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    elif filter_option == 'this_year':
        start_date = now.replace(month=1, day=1)
    elif filter_option == 'custom':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        start_date = now - timedelta(days=now.weekday())
        end_date = now

    changes = Change.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date).order_by('timestamp')
    
    # Create a CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="cashbook_report_{filter_option}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Name', 'Amount', 'Collected', 'Claimed', 'Balance'])

    balance = 0  
    for change in changes:
        if not change.collected:
            balance += change.amount

        writer.writerow([
            change.timestamp,
            change.name,
            change.amount,
            'collected' if change.collected else 'not collected',
            'claimed' if change.claimed else 'not claimed',
            balance,
        ])

    return response


@login_required
def create_change(request):
    #payload 
    """
        name:str,
        phonenumber:str,
        amount:float,
        receipt_number:str
    """
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            name = data.get('name')
            phonenumber = data.get('phonenumber')
            amount = Decimal(data.get('amount'))
            receipt_number = data.get('receipt_number')
            
            # validation
            if Change.objects.filter(receipt_number=receipt_number).exists():
                return JsonResponse({'success':False, 'message':f'Change with receipt number: {receipt_number} exists.'}, status=400)
            
            Change.objects.create(
                name=name,
                phonenumber=phonenumber,
                amount=amount,
                receipt_number=receipt_number,
                cashier=request.user,
                collected=False,
                claimed=False,
            )
            return JsonResponse({'success':True}, status=201)
        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}'}, status=400)
    return JsonResponse({'success':False, 'message':'Invalid request'}, status=405)

@login_required
def collect_change(request):
    # payload
    """
        change_id:id,
        amout:float
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            change_id = data.get('change_id')
            amount = data.get('amount')
            
            change = Change.objects.get(id=change_id)

            if amount == change.amount:
                change.collected = True

            elif amount < change.amount:
                change.amount -= amount
            else:
                return JsonResponse({'success':False, 'message':'Amount collected is more than the change amount'}, status=400)
            
            change.save()
            
            return JsonResponse({'success':True}, status=200)
        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}'}, status=400)
    return JsonResponse({'success':False, 'message':'Invalid request'}, status=405)

@login_required
def void_sales(request, user_id):
    if request.method == 'GET':
        sales = Sale.objects.filter(date=timezone.now()).order_by('-date')
        
        sale_items = SaleItem.objects.filter(sale__date=timezone.now())
    
        return render (request, 'pos/void_sales.html', {
            'sales':sales,
            'sale_items':sale_items,
            'user_id':user_id
        })
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            logger.info(f'Sales data for voiding: {data}')

            sale_id = data['sale_id']
            sale = get_object_or_404(Sale, id=sale_id)
            items = SaleItem.objects.filter(sale=sale)

            if sale.void:
                return JsonResponse({'success': False, 'message': 'Sale is already voided'}, status=400)

            with transaction.atomic():
                sale.void = True
                sale.save()

                logger.info(f'Sale marked as voided: {sale}')

                # for item in items:
                #     product = item.product or item.meal or item.dish

                #     if product:
                #         if isinstance(product, Product):

                #             product.quantity += item.quantity
                #             product.save()

                #             logger.info(f'Reverted product stock: {product}')

                #         elif isinstance(product, ProductionItems):
                #             product.portions_sold -= item.quantity
                #             product.left_overs += item.quantity
                #             product.save()

                #             logger.info(f'Reverted production item: {product}')

                #     item.delete()

                #     logger.info(f'Deleted sale item: {item}')
                
                change = Change.objects.filter(sale=sale).first()
                if change:
                    change.delete()
                    logger.info(f'Reverted cashbook entry: {change}')

                # Reverse the logs related to the sale
                try:
                    logs = ProductionLogs.objects.filter(sale=sale)
                    logs.delete()
                    logger.info(f'Reverted production logs for sale: {sale.id}')
                except:
                    logs = Logs.objects.filter(sale=sale)
                    logs.delete()
                    logger.info(f'Reverted Sale log: {sale.id}')

                # Revert cash book entry if it exists
                cashbook_entry = CashBook.objects.filter(sale=sale).first()
                if cashbook_entry:
                    cashbook_entry.delete()
                    logger.info(f'Reverted cashbook entry for sale: {sale.id}')

                # Return the response indicating success
                return JsonResponse({'success': True, 'message': 'Sale has been voided successfully'}, status=200)

        except Exception as e:
            logger.error(f'Error processing void transaction: {str(e)}')
            return JsonResponse({'success': True, 'message': f'{e}'}, status=400)


@login_required
def void_authenticate(request):
    from users.models import User

    if request.method == "POST":
        try:
            logger.info('here')
            data = json.loads(request.body)

            username = data.get("username")
            password = data.get("password")

            logger.info(username)

            if not username or not password:
                return JsonResponse({"success": False, "message": "Username and password are required."}, status=400)
            logger.info(username)
            user = User.objects.get(username=username)

            logger.info(user)

            if user.role in ['admin', 'accountant', 'supervisor', 'manager']:

                return JsonResponse({"success": True, "message": "Authentication successful.", "user_id":user.id}, status=200)
            else:
                return JsonResponse({"success": False, "message": "Invalid username or password."}, status=401)

        except Exception as e:
            return JsonResponse({"success": False, "message": f"An error occurred: {str(e)}"}, status=500)
        
@login_required
def cash_up(request, cashier_id):

    cash_in_hand = 0

    sales = Sale.objects.filter(cashier__id=cashier_id, date=datetime.datetime.today(), void=False).values('total_amount')
    change = Change.objects.filter(cashier__id=cashier_id, timestamp__date=datetime.datetime.today(), collected=False).values('amount')
    expenses = CashierExpense.objects.filter(cashier__id=cashier_id, date=datetime.datetime.today()).values('amount')

    total_sales = sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    total_change = change.aggregate(Sum('amount'))['amount__sum'] or 0 

    logger.info(total_sales)
    logger.info(total_expenses)
    logger.info(total_change)

    cash_in_hand = total_sales + total_change - total_expenses

    logger.info(f'cash in hand: {cash_in_hand}')

    data = {
        "total_sales":total_sales,
        'total_expenses':total_expenses,
        'total_change':total_change,
        'cash_in_hand':cash_in_hand
    }

    return JsonResponse({'success':True, 'data':data})
    


