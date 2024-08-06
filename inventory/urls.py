from django.urls import path
from .views import *


app_name = 'inventory'
#fdk
urlpatterns = [
    path('products/', products, name='products'),
    path('create/product/', product, name='product'),
    path('edit/product/<int:product_id>/', edit_inventory, name='edit_inventory'),
    path('product/detail/<int:product_id>/', product_detail, name='product_detail'),
    path('add/product/category/', add_product_category, name='add_product_category'),

    path('inventory/', inventory, name='inventory_list'),
    
    # unit of measurement 
    path('unit_of_measurement/', unit_of_measurement, name='unit_of_measurement'),
    
    # production plan 
    path('production/plan/list', production_plans, name='production_plans'),
    path('confirm_declaration/', confirm_declaration, name='confirm_declaration'),
    path('create/production/plan', create_production_plan, name='create_production_plan'),
    path('yesterdays/left/overs/', yeseterdays_left_overs, name='yeseterdays_left_overs'),
    path('declared/production/plan/', yeseterdays_left_overs, name='declared_production_plan'),
    path('update_production_plan/<int:pp_id>/', update_production_plan, name='update_production_plan'),
    path('production_plan/detail/<int:pp_id>/', production_plan_detail, name='production_plan_detail'),
    path('confirm/production_plan/<int:pp_id>/', confirm_production_plan, name='confirm_production_plan'),
    path('declare/production_plan/<int:pp_id>/', declare_production_plan, name='declare_production_plan'),
    path('processs/production_plan/<int:pp_id>/', process_production_plan_confirmation, name='process_production_plan'),
    
    # supplier
    path('suppliers/list', suppliers, name='suppliers'),
    path('edit/supplier/', edit_supplier, name='edit_supplier'),
    path('create/supplier/', create_supplier, name='create_supplier'),
    path('supplier/json/list/', supplier_list_json, name='supplier_list_json'),
    
    # ppurchase orders
    path('purchase_orders/list/', purchase_orders, name='purchase_orders'),
    path('print/purchase_order/<int:order_id>/', print_purchase_order, name='print_purchase_order'),
    path('purchase_order/create/', create_purchase_order, name='create_purchase_order'),
    path('purchase_order/receive/<int:order_id>/', receive_order, name='receive_order'),
    path('process/purchase_order/', process_received_order, name='process_received_order'),
    path('purchase_order/detail/<int:order_id>/', purchase_order_detail, name='purchase_order_detail'),
    path('purchase_order/delete/<int:purchase_order_id>/', delete_purchase_order, name='delete_purchase_order'),
    path('purchase_orders/status/<int:order_id>/', change_purchase_order_status, name='change_purchase_order_status'),
]