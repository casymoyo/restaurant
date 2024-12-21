from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Sum, Count
from datetime import date, timedelta, datetime
from finance.models import Sale, SaleItem
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

        sales_by_hour = SaleItem.objects.filter(sale__date=today) \
            .annotate(hour=ExtractHour('time')) \
            .values('hour') \
            .annotate(total_sales=Sum('price')) \
            .order_by('-total_sales')
        data['sales_by_hour'] = list(sales_by_hour)

        logger.info(data)

    elif filter_by == 'day':

        today_sales = Sale.objects.filter(date=today).aggregate(total=Sum('total_amount'))
        yesterday_sales = Sale.objects.filter(date=yesterday).aggregate(total=Sum('total_amount'))

        data['today_sales'] = today_sales['total'] or 0
        data['yesterday_sales'] = yesterday_sales['total'] or 0

    elif filter_by == 'month':

        month_sales = Sale.objects.filter(date__gte=start_of_month).aggregate(total=Sum('total_amount'))
        data['month_sales'] = month_sales['total'] or 0

    elif filter_by == 'year':
        
        year_sales = Sale.objects.filter(date__gte=start_of_year).aggregate(total=Sum('total_amount'))
        data['year_sales'] = year_sales['total'] or 0

    # Best-selling meal
    best_selling_meal = SaleItem.objects.values('meal__name') \
        .annotate(total_sold=Sum('quantity')) \
        .order_by('-total_sold') \
        .first()
    
    data['best_selling_meal'] = best_selling_meal

    meal_sales = SaleItem.objects.filter(meal__meal=True, sale__date=today)
    logger.info(f'today meal sales: {meal_sales}')

    dish_sales = SaleItem.objects.filter(dish__dish=True, sale__date=today)
    logger.info(f'today dish sales: {dish_sales}')\
    
    grouped_meals = defaultdict(lambda: {})
    grouped_dishes = defaultdict(lambda: {})

    sales = SaleItem.objects.select_related('sale', 'meal', 'dish').all()

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

    formatted_meals = {category: list(items.values()) for category, items in grouped_meals.items()}
    formatted_dishes = {category: list(items.values()) for category, items in grouped_dishes.items()}

    data['grouped_meals'] = dict(formatted_meals)
    data['grouped_dishes'] = dict(formatted_dishes)

    return JsonResponse(data)

def analytics_index(request):
    return render(request, 'analytics.html')
