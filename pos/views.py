import csv
import asyncio
import tempfile
import subprocess
import json, datetime
from loguru import logger
from decimal import Decimal
from datetime import timedelta
from django.db.models import Sum
from finance.models import Change
from django.db import transaction
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from finance.forms import ChangeForm
from asgiref.sync import sync_to_async
from django.utils.timezone import localdate
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from finance.models import Sale, SaleItem, CashBook, COGS
from django.contrib.auth.decorators import login_required
from inventory.models import ProductionRawMaterials, ProductionLogs
from inventory.models import Meal, Production, ProductionItems, Product, Logs
from permisions.permisions import (
    admin_required,
    sales_required
)
from django.views.decorators.cache import cache_page

@login_required
@cache_page(60*50)
def pos(request):
    meals = Meal.objects.filter(deactivate=False)
    
    return render(request, 'pos.html', 
        {
            'meals':meals,
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
async def process_sale(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data['items']
            staff = data['staff']
            order_type = data['order_type']
            received_amount = data.get('received_amount')
            
            sub_total = sum(item['price'] * item['quantity'] for item in items)
            tax = sub_total * 0.15
            total_amount = sub_total
            
            if staff:
                received_amount = total_amount

            # Wrap synchronous operations in sync_to_async
            try:
                kaolite = await sync_to_async(ProductionRawMaterials.objects.get)(product__name='Kaolite')
            except ProductionRawMaterials.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Please refill the stocks for kaolites'})

            try:
                salts = await sync_to_async(ProductionRawMaterials.objects.get)(product__name='salt sachets')
            except ProductionRawMaterials.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Please refill the stocks for salt sachets'})

            sale = await sync_to_async(Sale.objects.create)(
                total_amount=total_amount,
                tax=tax,
                sub_total=sub_total,
                cashier=request.user,
                staff=staff
            )

            today = localdate()
            cog = await sync_to_async(COGS.objects.filter(date=today).first)()
            daily_productions = await sync_to_async(Production.objects.filter(date_created=today).order_by('time_created'))()

            # Process items asynchronously
            for item in items:
                if not item['type']:
                    meal = await sync_to_async(Meal.objects.get)(id=item['meal_id'])
                    sale_item = await sync_to_async(SaleItem.objects.create)(
                        sale=sale,
                        meal=meal,
                        quantity=item['quantity'],
                        price=meal.price
                    )

                    async def log(products, sale_item):
                        for product in products:
                            await sync_to_async(ProductionLogs.objects.create)(
                                user=request.user, 
                                action='sale',
                                product=product,
                                quantity=sale_item.quantity,
                                total_quantity=product.quantity,
                            )

                    # Handling salts and kaolite quantities asynchronously
                    if order_type == 'sitting':
                        salts.quantity -= item['quantity']
                        cog.amount += salts.product.cost * item['quantity']
                        await log([salts], sale_item)
                    else:
                        salts.quantity -= item['quantity']
                        kaolite.quantity -= item['quantity']
                        cog.amount += (salts.product.cost * item['quantity'] + kaolite.product.cost * item['quantity'])
                        await log([salts, kaolite], sale_item)

                    # Save asynchronously
                    await sync_to_async(cog.save)()
                    await sync_to_async(salts.save)()
                    await sync_to_async(kaolite.save)()

                    for production in daily_productions:
                        try:
                            pp_item = await sync_to_async(ProductionItems.objects.get)(production=production, dish__in=meal.dish.all())
                            
                            if pp_item.portions == pp_item.portions_sold:
                                continue

                            if staff:
                                pp_item.staff_portions += sale_item.quantity
                            else:
                                pp_item.portions_sold += sale_item.quantity
                            
                            pp_item.left_overs -= sale_item.quantity
                            await sync_to_async(pp_item.save)()
                            break

                        except ProductionItems.DoesNotExist:
                            continue

                else:
                    product = await sync_to_async(Product.objects.get)(id=item['meal_id'])
                    product.quantity -= item['quantity']
                    sale_item = await sync_to_async(SaleItem.objects.create)(
                        sale=sale,
                        product=product,
                        quantity=item['quantity'],
                        price=product.price
                    )

                    cog.amount += product.cost * item['quantity']
                    await sync_to_async(Logs.objects.create)(
                        user=request.user, 
                        action='sale',
                        product=product,
                        quantity=sale_item.quantity,
                        total_quantity=product.quantity,
                    )

                    await sync_to_async(product.save)()

            await sync_to_async(CashBook.objects.create)(
                sale=sale, 
                amount=sale.total_amount,
                debit=True,
                description=f'Sale (Receipt number: {sale.receipt_number})'
            )

            await generate_receipt(request, sale, received_amount)

            return JsonResponse({'success': True, 'sale_id': sale.id}, status=201)

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


async def generate_receipt(request, sale, received_amount):
    # The receipt generation function can remain the same as long as PDF writing and printing can be handled asynchronously
    change = received_amount - sale.total_amount
    PAGE_WIDTH = 8 * cm
    PAGE_HEIGHT = 29.7 * cm
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = temp_pdf.name

    p = canvas.Canvas(pdf_path, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    font_size = 9
    p.setFont("Helvetica", font_size)

    def draw_centered_text(text, y_position, bold=False):
        if bold:
            p.setFont("Helvetica-Bold", font_size)
        else:
            p.setFont("Helvetica", font_size)
        text_width = p.stringWidth(text)
        x_position = (PAGE_WIDTH - text_width) / 2
        p.drawString(x_position, y_position, text)

    y_position = PAGE_HEIGHT - 1 * cm
    draw_centered_text("Pars Sales Investments", y_position, bold=True)
    y_position -= 0.5 * cm
    draw_centered_text("65 Speke Ave", y_position)
    y_position -= 0.5 * cm
    draw_centered_text("Harare", y_position)
    
    # Continue with other drawing as before...

    p.showPage()
    p.save()
    temp_pdf.close()

    try:
        printer_name = "EPSON TM-T88V"
        subprocess.run([r"C:\Users\PC\AppData\Local\SumatraPDF\SumatraPDF.exe", "-print-to", printer_name, pdf_path], check=True)
    except Exception as e:
        logger.error(f"Error printing the file: {e}")

@login_required
def change_list(request):
    filter_option = request.GET.get('filter', 'today')
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
        change_id:id
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            change_id = data.get('change_id')
            
            change = Change.objects.get(id=change_id)
            change.collected = True
            change.save()
            
            return JsonResponse({'success':True}, status=200)
        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}'}, status=400)
    return JsonResponse({'success':False, 'message':'Invalid request'}, status=405)
