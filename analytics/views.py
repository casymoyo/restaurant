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

    return JsonResponse(data)


def analytics_index(request):
    return render(request, 'analytics.html')
