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

        sales_by_hour = SaleItem.objects.filter(sale__date=today, void=False) \
            .annotate(hour=ExtractHour('time')) \
            .values('hour') \
            .annotate(total_sales=Sum('price')) \
            .order_by('-total_sales')
        data['sales_by_hour'] = list(sales_by_hour)

        logger.info(data)

    elif filter_by == 'day':

        today_sales = Sale.objects.filter(date=today, void=False).aggregate(total=Sum('total_amount'))
        yesterday_sales = Sale.objects.filter(date=yesterday).aggregate(total=Sum('total_amount'))

        data['today_sales'] = today_sales['total'] or 0
        data['yesterday_sales'] = yesterday_sales['total'] or 0

    elif filter_by == 'month':

        month_sales = Sale.objects.filter(date__gte=start_of_month, void=False).aggregate(total=Sum('total_amount'))
        data['month_sales'] = month_sales['total'] or 0

    elif filter_by == 'year':
        
        year_sales = Sale.objects.filter(date__gte=start_of_year, void=False).aggregate(total=Sum('total_amount'))
        data['year_sales'] = year_sales['total'] or 0

    # Best-selling dish
    best_selling_meal = SaleItem.objects.filter(meal__isnull=False).values('meal__name') \
    .annotate(total_sold=Sum('quantity')) \
    .order_by('-total_sold') \
    .first()

    best_selling_dish = SaleItem.objects.filter(dish__isnull=False).values('dish__name') \
    .annotate(total_sold=Sum('quantity')) \
    .order_by('-total_sold') \
    .first()


    combined_best_selling = []

    logger.info(best_selling_dish['dish__name'])
    logger.info(best_selling_meal['meal__name'])

    if best_selling_meal['meal__name']  == best_selling_dish['dish__name']:
        combined_best_selling.append(
            {
                'name': best_selling_meal['meal__name'], 
                'total_sold': best_selling_meal['total_sold'] + best_selling_dish['total_sold']
            }
        )
        data['combined_best_selling'] = combined_best_selling
    else:
        data['best_selling_meal'] = best_selling_meal
        data['best_selling_dish'] = best_selling_dish

    logger.info(f'best selling meal: {combined_best_selling}')
    
    grouped_meals = defaultdict(lambda: {})
    grouped_dishes = defaultdict(lambda: {})

    sales = SaleItem.objects.filter(sale__void=False).select_related('sale', 'meal', 'dish', 'product').all()

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

    data['grouped_meals'] = dict(formatted_meals)
    data['grouped_dishes'] = dict(formatted_dishes)

    return JsonResponse(data)

def analytics_index(request):
    return render(request, 'analytics.html')
