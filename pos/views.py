import tempfile
import subprocess
import json, datetime
from loguru import logger
from django.db import transaction
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from django.http import JsonResponse
from finance.models import Sale, SaleItem, CashBook
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from inventory.models import Meal, Production, ProductionItems, Product, Logs

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
    
from django.utils.timezone import localdate
from datetime import datetime

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
            
            tax = sub_total * 0.15 
            logger.info(tax)
            
            total_amount = sub_total
            
            sale = Sale.objects.create(
                total_amount=total_amount,
                tax=tax,
                sub_total=sub_total,
                cashier=request.user,
                staff=True if staff else False
            )

            today = localdate()
            daily_productions = Production.objects.filter(date_created=today).order_by('time_created')

            for item in items:
                if not item['type']:
                    meal = get_object_or_404(Meal, id=item['meal_id'])
                    
                    sale_item = SaleItem.objects.create(
                        sale=sale,
                        meal=meal,
                        quantity=item['quantity'],
                        price=meal.price
                    )
                    
                    for production in daily_productions:
                        try:
                            pp_item = ProductionItems.objects.get(production=production, dish__in=meal.dish.all())
                            
                            if pp_item.portions == pp_item.portions_sold:
                                continue  # Move to the next production plan if portions are exhausted

                            if staff:
                                pp_item.staff_portions += sale_item.quantity
                                logger.info('staff')
                            else:
                                pp_item.portions_sold += sale_item.quantity
                                logger.info('sale')
                                
                            pp_item.left_overs -= sale_item.quantity
                            pp_item.save()
                            
                            break  # Stop checking further productions for this dish
                        
                        except ProductionItems.DoesNotExist:
                            logger.info(f'Production item not found for dish.')
                            continue  # Move to the next production plan if not found
                        
                else:
                    product = get_object_or_404(Product, id=item['meal_id'])
                    product.quantity -= item['quantity']
                    
                    sale_item = SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=item['quantity'],
                        price=product.price  # Make sure to use the correct price here
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
                
                # generate_receipt(request, sale)
                    
            logger.info(f'Sale: {sale.id} Processed')
            return JsonResponse({'success': True, 'sale_id': sale.id}, status=201)

        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f'Error processing sale: {str(e)}')
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

        
@login_required
def generate_receipt(request, sale):
    #  page size to 8 cm by 9 cm
    PAGE_WIDTH = 8 * cm
    PAGE_HEIGHT = 29.7 * cm 

    # temporary file to store the PDF
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = temp_pdf.name

    p = canvas.Canvas(pdf_path, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

    # font size (12 px is roughly equivalent to 9 pt in ReportLab)
    font_size = 9  # points
    p.setFont("Helvetica", font_size)

    def draw_centered_text(text, y_position, bold=False):
        if bold:
            p.setFont("Helvetica-Bold", font_size)
        else:
            p.setFont("Helvetica", font_size)
        text_width = p.stringWidth(text)
        x_position = (PAGE_WIDTH - text_width) / 2
        p.drawString(x_position, y_position, text)

    # starting positions
    y_position = PAGE_HEIGHT - 1 * cm

    # title and company info
    draw_centered_text("Pars Sales Investments", y_position, bold=True)
    y_position -= 0.5 * cm
    draw_centered_text("65 Speke Ave", y_position)
    y_position -= 0.5 * cm
    draw_centered_text("Harare", y_position)

    # "TAX INVOICE" header
    y_position -= 0.7 * cm
    draw_centered_text("**TAX INVOICE**", y_position, bold=True)

    # tax and TIN numbers
    y_position -= 0.5 * cm
    p.drawString(1 * cm, y_position, "TAX NR : 220356643")
    y_position -= 0.5 * cm
    p.drawString(1 * cm, y_position, "TIN No: 2001020099")

    # item and price details
    for sale in SaleItem.objects.filter(sale=sale):
        y_position -= 0.7 * cm
        p.drawString(1 * cm, y_position, f"{sale.meal}")
        p.drawString(4.5 * cm, y_position, f"{sale.quantity} @")
        p.drawString(6 * cm, y_position, f"${sale.price}")

    # totals
    y_position -= 0.7 * cm
    p.drawString(1 * cm, y_position, "TAX :")
    p.drawString(6 * cm, y_position, f"{sale.tax}")

    y_position -= 0.5 * cm
    p.drawString(1 * cm, y_position, "TOTAL :")
    p.setFont("Helvetica-Bold", font_size)
    p.drawString(6 * cm, y_position, f"{sale.total_amount}")

    y_position -= 0.5 * cm
    p.setFont("Helvetica", font_size)
    p.drawString(1 * cm, y_position, "Cash :")
    p.drawString(6 * cm, y_position, f"{sale}")

    y_position -= 0.5 * cm
    p.drawString(1 * cm, y_position, "Change :")
    p.drawString(6 * cm, y_position, "$0.00")

    # cashier and transaction info
    y_position -= 0.7 * cm
    p.drawString(1 * cm, y_position, "Cashier :")
    p.drawString(6 * cm, y_position, f"{request.user}")

    # date and time
    y_position -= 0.5 * cm
    now = datetime.datetime.now().strftime("%a %d %m, %Y %H:%M")
    p.drawString(1 * cm, y_position, "Date :")
    p.drawString(6 * cm, y_position, now)

    # transaction number
    y_position -= 0.5 * cm
    p.drawString(1 * cm, y_position, "Transaction :")
    p.drawString(6 * cm, y_position, "45512425105404")

    y_position -= 0.5 * cm
    p.drawString(1 * cm, y_position, "Sales Channel :")
    p.drawString(6 * cm, y_position, "USD")

    # y_position -= 0.7 * cm
    # p.drawString(1 * cm, y_position, "Total Qty :")
    # p.drawString(6 * cm, y_position, "1")
    # y_position -= 1 * cm
    draw_centered_text("Thank You Call Again", y_position, bold=True)

    y_position -= 0.5 * cm
    draw_centered_text("www.techcity.co.zw", y_position)

    p.showPage()
    p.save()
    
    # Close the temporary file
    temp_pdf.close()
    
    logger.info(pdf_path)
    
    try:
        printer_name = "EPSON TM-T88V"  
       
        subprocess.run([
            r"C:\Users\PC\AppData\Local\SumatraPDF\SumatraPDF.exe", 
            "-print-to",
            printer_name,
            pdf_path
        ], check=True)
    except Exception as e:
        logger.error(f"Error printing the file: {e}")


