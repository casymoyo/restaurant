from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Sum, Count
from datetime import date, timedelta, datetime
from finance.models import Sale, SaleItem, Change
from loguru import logger
from django.http import JsonResponse
from django.db.models import Sum
from datetime import date, timedelta
from django.db.models.functions import ExtractHour
from collections import defaultdict


def analytics_view(request):
    # Get filter parameters
    filter_by = request.GET.get('filter_by', 'day')
    today = date.today()
    yesterday = today - timedelta(days=1)
    start_of_month = today.replace(day=1)

    data = {}

    if filter_by == 'hour':

        sales_by_hour = SaleItem.objects.filter(sale__date=today, void=False) \
            .annotate(hour=ExtractHour('time')) \
            .values('hour') \
            .annotate(total_sales=Sum('price')) \
            .order_by('-total_sales')
        data['sales_by_hour'] = list(sales_by_hour)

        logger.info(data)

    elif filter_by == 'day':

        today_sales = Sale.objects.filter(date=today, void=False).aggregate(total=Sum('total_amount'))
        yesterday_sales = Sale.objects.filter(date=yesterday, void=False).aggregate(total=Sum('total_amount'))
        
        today_void_sales = Sale.objects.filter(date=today, void=True).aggregate(total=Sum('total_amount'))
       
        yesterday_void_sales = Sale.objects.filter(date=yesterday, void=True).aggregate(total=Sum('total_amount'))
        
        change_amount = Change.objects.filter(timestamp__date=today, collected=False).aggregate(total=Sum('amount'))
        yesterday_change_amount = Change.objects.filter(timestamp__date=yesterday, collected=False).aggregate(total=Sum('amount'))

        data['total_void_sales'] = today_void_sales['total'] or 0
        data['change_amount'] = change_amount['total'] or 0
        data['yesterday_change_amount'] = yesterday_change_amount['total'] or 0

        data['today_sales'] = today_sales['total'] or 0
        data['yesterday_sales'] = yesterday_sales['total'] or 0
        data['yesterday_void_sales'] = yesterday_void_sales['total'] or 0
        
    elif filter_by == 'month':

        month_sales = Sale.objects.filter(date__gte=start_of_month, void=False).aggregate(total=Sum('total_amount'))
        data['month_sales'] = month_sales['total'] or 0

    elif filter_by == 'year':
        
        year_sales = Sale.objects.filter(date__gte=start_of_year, void=False).aggregate(total=Sum('total_amount'))
        data['year_sales'] = year_sales['total'] or 0

    # Best-selling dish
    best_selling_meal = SaleItem.objects.filter(meal__isnull=False, sale__date=today).values('meal__name') \
    .annotate(total_sold=Sum('quantity')) \
    .order_by('-total_sold') \
    .first()

    best_selling_dish = SaleItem.objects.filter(dish__isnull=False, sale__date=today).values('dish__name') \
    .annotate(total_sold=Sum('quantity')) \
    .order_by('-total_sold') \
    .first()

    # logger.info(best_selling_dish['dish__name'])
    # logger.info(best_selling_meal['meal__name'])
   
    data['best_selling_meal'] = best_selling_meal or ''
    data['best_selling_dish'] = best_selling_dish or ''
    
    
    grouped_meals = defaultdict(lambda: {})
    grouped_dishes = defaultdict(lambda: {})
    staff_dishes = defaultdict(lambda: {})

    sales = SaleItem.objects.filter(sale__void=False, sale__staff=False).select_related('sale', 'meal', 'dish', 'product').all()

    staff_sales = SaleItem.objects.filter(sale__void=False, sale__staff=True).select_related('sale', 'meal', 'dish', 'product').all()

    sales_dishes = SaleItem.objects.filter(sale__void=False, sale__staff=False)

    dishes = defaultdict(lambda: {})


    for sale in sales_dishes:
        if sale.meal:
            sale_date = sale.sale.date
            category = (
                'Today' if sale_date == today
                else 'Yesterday' if sale_date == yesterday
                else sale_date.strftime('%A, %d %B %Y')
            )
            for dish in sale.meal.dish.all():
                if dish.name in dishes[category]:
                    dishes[category][dish.name]['quantity'] += sale.quantity
                    dishes[category][dish.name]['price'] += sale.price * sale.quantity
                else:
                    dishes[category][dish.name] = {
                        'name': dish.name,
                        'quantity': sale.quantity,
                        'price': sale.price * sale.quantity,
                    }

    for sale in staff_sales:
        sale_date = sale.sale.date
        category = (
            'Today' if sale_date == today
            else 'Yesterday' if sale_date == yesterday
            else sale_date.strftime('%A, %d %B %Y')
        )
        
        if sale.meal:
            for dish in sale.meal.dish.all():
                if dish.name in staff_dishes[category]:
                    staff_dishes[category][dish.name]['quantity'] += sale.quantity
                    staff_dishes[category][dish.name]['price'] += sale.price * sale.quantity
                else:
                    staff_dishes[category][dish.name] = {
                        'name': dish.name,
                        'quantity': sale.quantity,
                        'price': sale.price * sale.quantity,
                    }
        elif sale.dish:
                dish_name = sale.dish.name
                if dish_name in staff_dishes[category]:

                    staff_dishes[category][dish_name]['quantity'] += sale.quantity
                    staff_dishes[category][dish_name]['price'] += sale.price * sale.quantity
                else:
                    staff_dishes[category][dish_name] = {
                        'name': dish_name,
                        'quantity': sale.quantity,
                        'price': sale.price * sale.quantity,
                    }
                    

    formatted_staff_dishes = {category: list(items.values()) for category, items in staff_dishes.items()}
    data['staff_dishes'] = dict(formatted_staff_dishes)

    logger.info(staff_dishes) 

    if not sales:
        logger.warning("No sales data found.")
    else:
        for sale in sales:
            sale_date = sale.sale.date
            category = (
                'Today' if sale_date == today
                else 'Yesterday' if sale_date == yesterday
                else sale_date.strftime('%A, %d %B %Y')
            )

            if sale.meal:
                meal_name = sale.meal.name
                if meal_name in grouped_meals[category]:
                    grouped_meals[category][meal_name]['quantity'] += sale.quantity
                    grouped_meals[category][meal_name]['price'] += sale.price * sale.quantity
                else:

                    grouped_meals[category][meal_name] = {
                        'name': meal_name,
                        'quantity': sale.quantity,
                        'price': sale.price * sale.quantity,
                    }

            elif sale.dish:
                dish_name = sale.dish.name
                if dish_name in grouped_dishes[category]:

                    grouped_dishes[category][dish_name]['quantity'] += sale.quantity
                    grouped_dishes[category][dish_name]['price'] += sale.price * sale.quantity
                else:
                    grouped_dishes[category][dish_name] = {
                        'name': dish_name,
                        'quantity': sale.quantity,
                        'price': sale.price * sale.quantity,
                    }
                    
            elif sale.product:
                product_name = sale.product.name
                if product_name in grouped_dishes[category]:
                    grouped_dishes[category][product_name]['quantity'] += sale.quantity
                    grouped_dishes[category][product_name]['price'] += sale.price * sale.quantity
                else:
                    grouped_dishes[category][product_name] = {
                        'name': product_name,
                        'quantity': sale.quantity,
                        'price': sale.price * sale.quantity,
                    }

    formatted_meals = {category: list(items.values()) for category, items in grouped_meals.items()}
    formatted_dishes = {category: list(items.values()) for category, items in grouped_dishes.items()}
    f_dishes = {category: list(items.values()) for category, items in dishes.items()}

    combined_dishes = defaultdict(lambda: {})

    for category, items in grouped_dishes.items():
        for dish_name, dish_data in items.items():
            if dish_name in combined_dishes[category]:
                combined_dishes[category][dish_name]['quantity'] += dish_data['quantity']
                combined_dishes[category][dish_name]['price'] += dish_data['price']
            else:
                combined_dishes[category][dish_name] = dish_data.copy()

    for category, items in dishes.items():
        for dish_name, dish_data in items.items():
            if dish_name in combined_dishes[category]:
                combined_dishes[category][dish_name]['quantity'] += dish_data['quantity']
                combined_dishes[category][dish_name]['price'] += dish_data['price']
            else:
                combined_dishes[category][dish_name] = dish_data.copy()

    # Convert combined_dishes to the desired format
    f_dishes = {category: list(items.values()) for category, items in combined_dishes.items()}

    data['dishes'] = dict(f_dishes)
    data['grouped_meals'] = dict(formatted_meals)
    data['grouped_dishes'] = dict(formatted_dishes)

    return JsonResponse(data)

def analytics_index(request):
    return render(request, 'analytics.html')
