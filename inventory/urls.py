from django.urls import path
from .views import *


app_name = 'inventory'

urlpatterns = [
    path('products/', products, name='products'),
    path('create/product/', product, name='product'),
    path('edit/product/<int:product_id>/', edit_inventory, name='edit_inventory'),
    path('product/detail/<int:product_id>/', product_detail, name='product_detail'),
    path('add/product/category/', add_product_category, name='add_product_category'),
    path('raw_material_json/', raw_material_json, name='raw_material_json'),

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
    path('process/production_plan/<int:pp_id>/', process_production_plan_confirmation, name='process_production_plan'),
    path('process/minor_raw_materials/<int:pp_id>/', process_raw_materials, name='process_minor_raw_materials'),
    path('minor_raw_materials/<int:pp_id>/', minor_raw_materials, name='minor_raw_materials'),
    path('confirm/minor_raw_materials/<int:pp_id>/', confirm_minor_raw_materials, name='confirm_minor_raw_materials'),
    path('confirm/minor_raw_materials/', confirm_minor_raw, name='confirm_minor_raw'),
    path('production_raw_materials/', production_raw_materials, name='production_raw_materials'),
    path('production_rm/detail/<int:rm_id>/', production_rm_detail, name='production_rm_detail'),
    
    # supplier
    path('suppliers/list', suppliers, name='suppliers'),
    path('edit/supplier/', edit_supplier, name='edit_supplier'),
    path('create/supplier/', create_supplier, name='create_supplier'),
    path('supplier/json/list/', supplier_list_json, name='supplier_list_json'),
    path('supplier_prices/<str:raw_material_name>/', supplier_prices, name='supplier_prices'),

    #to remove
    path('home', p_home, name='p_home'),
    
    # ppurchase orders
    path('purchase_orders/list/', purchase_orders, name='purchase_orders'),
    path('print/purchase_order/<int:order_id>/', print_purchase_order, name='print_purchase_order'),
    path('purchase_order/create/', create_purchase_order, name='create_purchase_order'),
    path('purchase_order/receive/<int:order_id>/', receive_order, name='receive_order'),
    path('process/purchase_order/', process_received_order, name='process_received_order'),
    path('purchase_order/detail/<int:order_id>/', purchase_order_detail, name='purchase_order_detail'),
    path('purchase_order/delete/<int:purchase_order_id>/', delete_purchase_order, name='delete_purchase_order'),
    path('purchase_orders/status/<int:order_id>/', change_purchase_order_status, name='change_purchase_order_status'),
    
    # dishes
    path('dishes/', DishListView.as_view(), name='dish_list'),
    path('edit_dish/<int:dish_id>/', edit_dish, name='edit_dish'),
    path('create/dish/', add_dish, name='dish_create'),
    path('dishes/<int:pk>/edit/', DishUpdateView.as_view(), name='dish_update'),
    path('dishes/<int:pk>/delete/', DishDeleteView.as_view(), name='dish_delete'),
    path('dish_json_detail/', dish_json_detail, name='dish_json_detail'),
    path('dish_data_json/<int:dish_id>/', get_dish_data, name='dish_json'),
    
    # ingridients
    path('ingredients/', IngredientListView.as_view(), name='ingredient_list'),
    path('ingredients/<int:pk>/edit/', IngredientUpdateView.as_view(), name='ingredient_update'),
    path('ingredients/<int:pk>/delete/', IngredientDeleteView.as_view(), name='ingredient_delete'),
    
    # meals
    path('add/meal/', add_meal, name='add_meal'),
    path('meal/list', meal_list, name='meal_list'),
    path('meals/<int:meal_id>/edit/', edit_meal, name='edit_meal'),
    path('meals/delete/<int:meal_id>/', delete_meal, name='delete_meal'),
    path('create/meal/category/', create_meal_category, name='create_meal_category'),
    
    # end of day
    path('end-of-day/', end_of_day_view, name='end_of_day_view'),
    path('save-end-of-day/', end_of_day_view, name='save_end_of_day'),
    path('confirm_end_of_day/', confirm_end_of_day, name='confirm_end_of_day'),
    path('end_of_day_detail/<int:e_o_d_id>/', end_of_day_detail, name='end_of_day_detail'),
    path('end_of_day_list/', end_of_day_list, name='end_of_day_list'),
    
    # reorder_lis
    path('order_list', order_list, name='order_list'),
    
    # transfers
    path('transfers', transfers, name='transfers'),
    path('add/transfer/', transfer_to_production, name='add_transfer'),
    path('accept_transfer/<int:transfer_id>/', accept_transfer, name='accept_transfer'),
    path('production_transfers/', production_transfers, name='production_transfers'),
    path('receive_transfer_detail/<int:transfer_id>/', receive_transfers_detail, name='receive_transfer_detail'),
    
    # production sales
    path('production_sales/', production_sales, name='production_sales'),
    
    # check_list
    path('check_list/', check_check_list, name='check_check_list')
]