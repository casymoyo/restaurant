from django.urls import path
from . views import *

app_name = 'pos'

urlpatterns = [
    path('pos/', pos, name='pos' ),
    path('process/sale/', process_sale, name='process_sale'),
    path('meal/detail/json/<int:meal_id>/', meal_detail_json, name='meal_detail_json')
]