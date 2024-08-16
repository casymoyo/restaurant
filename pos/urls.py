from django.urls import path
from . views import *

app_name = 'pos'

urlpatterns = [
    path('', pos, name='pos' ),
    path('process/sale/', process_sale, name='process_sale'),
    path('sales/list', sales_list, name='sales_list'),
    path('download-receipt/', generate_receipt_pdf, name='download_receipt'),
    path('product_meal_json/', product_meal_json, name='product_meal_json'),
    path('meal/detail/json/<int:meal_id>/', meal_detail_json, name='meal_detail_json')
]