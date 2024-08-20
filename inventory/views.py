import json, threading
from django.utils import timezone
from . models import *
from loguru import logger
from decimal import Decimal
from django.views import View    
from django.contrib import messages 
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from loguru import logger
from django.contrib.auth import get_user_model
from .models import Dish, Ingredient
from django.views import View
from django.urls import reverse
from django.db.models import Sum
from django.utils.timezone import localdate
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
import io
from utils.email import EmailThread
from django.core.mail import EmailMessage
from finance.models import COGS
from .tasks import send_production_creation_notification

from finance.models import (
    Sale,
    SaleItem,
    CashBook,
    Expense, 
    ExpenseCategory
)

from . forms import (
    MealForm,
    AddProductForm,
    AddSupplierForm,
    CreateOrderForm,
    noteStatusForm,
    PurchaseOrderStatus,
    UnitOfMeasurementForm,
    EditProductForm,
    ProductionPlanInlineForm,
    DishForm, 
    IngredientForm
)


def unit_of_measurement(request):
    if request.method == 'GET':
        units = UnitOfMeasurement.objects.all().values()
        return JsonResponse(list(units), safe=False)
    
    if request.method == 'POST':
        # payload 
        """"
            name
        """
        try:
            data = json.loads(request.body)
            unit_name = data.get('name')
        except Exception as e:
            return JsonResponse({'success':False, 'message':'Invalid Json data'}, status=400)
        
        if unit_name:
            unit_name = unit_name.lower()
            
            #validation for existance
            if UnitOfMeasurement.objects.filter(unit_name=unit_name).exists():
                logger.info(f'{unit_name}, exists')
                return JsonResponse({'success':False, 'message':f'Unit of Measurement with the name {unit_name} exists'}, status=400)
            
            unit_obj = UnitOfMeasurement(
                unit_name=unit_name
            )
            unit_obj.save()
            logger.info(f'{unit_obj.unit_name}, successfully created')
            return JsonResponse({'success':True}, status=200)
        
        logger.info(f'unit of measurement -> bad request')
        return JsonResponse({'success':False, 'message':'Unit of measurement is invalid'}, status=400)
    
    logger.info(f'unit of measurement -> bad request')
    return JsonResponse({'success':False, 'message':'Invalid request'}, status=400)
                  

# @login_required
def products(request):
    raw_materials = Product.objects.filter()
    return render(request, 'inventory/products.html', 
        {
            'raw_materials':raw_materials,
        }
    )

# @login_required
def inventory(request):
    product_name = request.GET.get('name', '')
    if product_name:
        
        return JsonResponse(list(Product.objects.filter(name=product_name).values(
                'unit__unit_name',
                'name',
                'id'
            )), safe=False)
    return JsonResponse({'error':'product doesnt exists'})


def add_product_category(request):
    categories = Category.objects.all().values()
    
    if request.method == 'POST':
        data = json.loads(request.body)
        category_name = data['name']
        
        if Category.objects.filter(name=category_name).exists():
            return JsonResponse({'error', 'Category Exists'})
        
        Category.objects.create(
            name=category_name
        )
    return JsonResponse(list(categories), safe=False)   

def product(request):

    if request.method == 'POST':
        # payload
        """
            name,
            price: float,
            cost: float,
            unit of measurement: int,
            quantity: int,
            category,
            tax_type,
            min_stock_level,
            portion_multiplier: int
            description
            raw_material:bool,
            finished_product:bool
        """
        try:
            data = json.loads(request.body)
        except Exception as e:
            return JsonResponse({'success':False, 'message':'Invalid data'})
        
        
        # validation for existance
        if Product.objects.filter(name=data['name']).exists():
            return JsonResponse({'success':False, 'message':f'Product exists'})

        try:
            category = Category.objects.get(id=data['category'])
        except Category.DoesNotExist:
            return JsonResponse({'success':False, 'message':f'Category doesn\'t Exists'})
        
        try: 
            unit = UnitOfMeasurement.objects.get(id=int(data['unit']))
        except Exception as e:
            return JsonResponse({'success':False, 'message':f'Unit of Measurement Doesnt Exists'})
        
        product = Product.objects.create(
            name = data['name'],
            price = data['price'],
            cost = data['cost'],
            quantity = data['quantity'],
            category = category,
            tax_type = data['tax_type'],
            min_stock_level = data['min_stock_level'],
            description = data['description'], 
            raw_material = True if data['raw_material'] else False,
            finished_product = True if data['finished_product'] else False,
            unit = unit,
        )
        product.save()
        logger.info(f'product saved')
        return JsonResponse({'success':True})
            
    if request.method == 'GET':
        products = Product.objects.all().values(
            'id',
            'name',
        )
        return JsonResponse(list(products), safe=False)
    
    return JsonResponse({'success':False, 'message':'Invalid request'})

def finished_products(request):
    # as defined as products in the UI
    products = Product.objects.filter(raw_material = False)
    logger.info(products)
    return render(request, 'inventory/finished_goods.html', 
        {
            'products':products
        }
    )

def product_detail(request, product_id):
    try: 
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        messages.warning(request, f'Product with ID: {product_id} doesn\'t exists')
        
    logs = Logs.objects.filter(product=product)

    return render(request, 'inventory/product_detail.html', 
        {
            'product': product,
            'logs': logs,
        }
    )

def edit_inventory(request, product_id):
    
    try: 
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        messages.warning(request, f'Product with ID: {product_id} doesn\'t exists')
        
    form = EditProductForm(instance=product)

    if request.method == 'POST':
        form = EditProductForm(request.POST, instance=product)
        
        if form.is_valid():
            form.save()
            
        Logs.objects.create(
            user=request.user, 
            action= 'Edit',
            product=product,
            quantity=product.quantity,
            total_quantity=product.quantity,
        )
        
        messages.success(request, f'{product.name} update succesfully')
        return redirect('inventory:products')
    
    return render(request, 'inventory/edit_product.html', 
            {
                'form':form,
                'product':product
            }
        )

# @login_required
def suppliers(request):
    form = AddSupplierForm()
    suppliers = Supplier.objects.all()
    return render(request, 'inventory/suppliers.html', 
        {
            'suppliers':suppliers,
            'form':form
        }
    )

# @login_required
def supplier_list_json(request):
    suppliers = Supplier.objects.all().values(
        'id',
        'name'
    )
    return JsonResponse(list(suppliers), safe=False)

# @login_required
def create_supplier(request):
    #payload
    """
        name 
        contact
        email
        phone 
        address
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        
        name = data['name']
        contact = data['contact']
        email = data['email']
        phone = data['phone']
        address = data['address']
        
        if not name or not contact or not email or not phone or not address:
            return JsonResponse({'success': False, 'message':'Fill in all the form data'}, status=400)
        
        if Supplier.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message':f'Supplier{name} already exists'}, status=400)
        
        supplier = Supplier(
            name = name,
            contact_name = contact,
            email = email,
            phone = phone,
            address = address
        )
        supplier.save()
        logger.info(f'Supplier successfully created {supplier.name}')
        return JsonResponse({'success': True}, status=200)
        
# @login_required
def edit_supplier(request, supplier_id):
    # payload
    """
        supplier_id
    """
    
    if request.method == 'POST':
        data = json.loads(request.post)
        supplier_id = data['supplier_id']
        
        if supplier_id:
            try:
                supplier = Supplier.objects.get(id=supplier_id)
            except Exception as e:
                return JsonResponse({'success': False, 'message':f'{supplier_id} doesn\'t exists'}, status=400)
                
        form = AddSupplierForm(request.post, instance=supplier)
        
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True}, status=400)
    return JsonResponse({'success': True})

# @login_required
def purchase_orders(request):
    form = CreateOrderForm()
    status_form = PurchaseOrderStatus()
    orders = PurchaseOrder.objects.filter()
    return render(request, 'inventory/purchase_orders.html', 
        {
            'form':form,
            'orders':orders,
            'status_form':status_form 
        }
    )
    
# @login_required
def create_purchase_order(request):
    
    # include the vat account and the purchase order account and the cash account
    
    if request.method == 'GET':
        supplier_form = AddSupplierForm()
        product_form = AddProductForm()
        suppliers = Supplier.objects.all()
        note_form = noteStatusForm()
        unit_form = UnitOfMeasurementForm()
        
        return render(request, 'inventory/create_purchase_order.html',
            {
                'product_form':product_form,
                'supplier_form':supplier_form,
                'suppliers':suppliers,
                'note_form':note_form,
                'unit_form':unit_form
            }
        )

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            purchase_order_data = data.get('purchase_order', {})
            purchase_order_items_data = data.get('po_items', [])
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON payload'}, status=400)

        supplier_id = purchase_order_data['supplier']
        delivery_date = purchase_order_data['delivery_date']
        status = purchase_order_data['status']
        notes = purchase_order_data['notes']
        total_cost = Decimal(purchase_order_data['total_cost'])
        discount = Decimal(purchase_order_data['discount'])
        handling_amount = Decimal(purchase_order_data['handling_amount'])
        tax_amount = Decimal(purchase_order_data['tax_amount'])
        other_amount = Decimal(purchase_order_data['other_amount'])
    
        if not all([supplier_id, delivery_date, status, total_cost, tax_amount]):
            return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)

        try:
            supplier = Supplier.objects.get(id=supplier_id)
        except Supplier.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Supplier with ID {supplier_id} not found'}, status=404)

        try:
            with transaction.atomic():
                purchase_order = PurchaseOrder(
                    order_number=PurchaseOrder.generate_order_number(),
                    supplier=supplier,
                    delivery_date=delivery_date,
                    status=status,
                    notes=notes,
                    total_cost=total_cost,
                    discount=discount,
                    tax_amount=tax_amount,
                    handling_amount=handling_amount,
                    other_amount=other_amount,
                    is_partial = False,
                    received = False
                )
                purchase_order.save()

                for item_data in purchase_order_items_data:
                    product_name = (item_data['product'])
                    quantity = float(item_data['quantity'])
                    unit_cost = Decimal(item_data['price'])
                    note = item_data['note']

                    if not all([product_name, quantity, unit_cost]):
                        transaction.set_rollback(True)
                        return JsonResponse({'success': False, 'message': 'Missing fields in item data'}, status=400)

                    try:
                        product = Product.objects.get(name=product_name)
                    except Product.DoesNotExist:
                        transaction.set_rollback(True)
                        return JsonResponse({'success': False, 'message': f'Product with Name {product_name} not found'}, status=404)

                    PurchaseOrderItem.objects.create(
                        purchase_order=purchase_order,
                        product=product,
                        quantity=quantity,
                        unit_cost=unit_cost,
                        received_quantity=0,
                        received=False,
                        note=note
                    )

                    # consider to put expenses
                if purchase_order.status == 'received':
                    category, _ = ExpenseCategory.objects.get_or_create(
                        name = 'Inventory'
                    )
                    
                    expense = Expense.objects.create(
                        category = category,
                        amount = purchase_order.total_cost,
                        user = request.user,
                        description = f'Expense purchase order{purchase_order.order_number}',
                        cancel = False
                    )
                    
                    CashBook.objects.create(
                        amount = purchase_order.total_cost,
                        expense = expense,
                        credit = True,
                        description = f'Expense purchase order{purchase_order.order_number}',
                    )
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

        return JsonResponse({'success': True, 'message': 'Purchase order created successfully'})
    
# @login_required
@transaction.atomic
def change_purchase_order_status(request, order_id):
    try:
        purchase_order = PurchaseOrder.objects.get(id=order_id)
    except PurchaseOrder.DoesNotExist:
        return JsonResponse({'error': f'Purchase order with ID: {order_id} doesn\'t exist'}, status=404)

    try:
        data = json.loads(request.body)
        status = data['status']
        
        if status:
            purchase_order.status=status
            if purchase_order.status == 'received':
                purchase_order.save()
                
                category, _ = ExpenseCategory.objects.get_or_create(
                    name = 'Inventory'
                )
                
                expense = Expense.objects.create(
                    category = category,
                    amount = purchase_order.total_cost - purchase_order.tax_amount,
                    user = request.user,
                    description = f'Expense purchase order{purchase_order.order_number}',
                    cancel = False
                )
                
                CashBook.objects.create(
                    amount = purchase_order.total_cost,
                    expense = expense,
                    credit = True,
                    description = f'Expense purchase order{purchase_order.order_number}',
                )
            
            return JsonResponse({'success':True}, status=200)
        else:
            return JsonResponse({'success':False, 'message':'Status is required'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON payload'}, status=400)

# @login_required
def print_purchase_order(request, order_id):
    try:
        purchase_order = PurchaseOrder.objects.get(id=order_id)
    except PurchaseOrder.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} doesn\'t exists')
        return redirect('inventory:purchase_orders')
    
    try:
        purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order)
    except PurchaseOrderItem.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} doesn\'t exists')
        return redirect('inventory:purchase_orders')
    
    return render(request, 'inventory/print_purchase_order.html', 
        {
            'orders':purchase_order_items,
            'purchase_order':purchase_order
        }
    )

# @login_required
def purchase_order_detail(request, order_id):
    try:
        purchase_order = PurchaseOrder.objects.get(id=order_id)
    except PurchaseOrder.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} doesn\'t exists')
        return redirect('inventory:purchase_orders')
    
    try:
        purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order)
    except PurchaseOrderItem.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} doesn\'t exists')
        return redirect('inventory:purchase_orders')
    
    return render(request, 'inventory/purchase_order_detail.html', 
        {
            'orders':purchase_order_items,
            'purchase_order':purchase_order
        }
    )
    
# @login_required
def delete_purchase_order(request, purchase_order_id):
    if request.method != "DELETE":
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

    try:
        purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
    except PurchaseOrder.DoesNotExist:
        return JsonResponse({'success': False, 'message': f'Purchase order with ID {purchase_order_id} not found'}, status=404)

    try:
        purchase_order.delete()
        return JsonResponse({'success': True, 'message': 'Purchase order deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def receive_order(request, order_id):
    try:
        purchase_order = PurchaseOrder.objects.get(id=order_id)
    except PurchaseOrder.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} doesn\'t exists')
        return redirect('inventory:purchase_orders')
    
    try:
        purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order)
    except PurchaseOrderItem.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} does not exists')
        return redirect('inventory:purchase_orders')
    
    return render(request, 'inventory/receive_order.html', 
        {
            'orders':purchase_order_items,
            'purchase_order':purchase_order
        }
    )
    
@login_required
@transaction.atomic
def process_received_order(request):
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON payload'}, status=400)

        order_item_id = data.get('id')
        quantity = data.get('quantity', 0)

        if not order_item_id or not isinstance(quantity, int) or quantity <= 0:
            return JsonResponse({'success': False, 'message': 'Invalid data'}, status=400)

        try:
            order_item = PurchaseOrderItem.objects.get(id=order_item_id)
        except PurchaseOrderItem.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Purchase Order Item with ID: {order_item_id} doesn\'t exist'}, status=404)

        try:
            purchase_order = PurchaseOrder.objects.get(order_number=order_item.purchase_order.order_number)
        except PurchaseOrderItem.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Purchase Order Item with Order number: {order_item.order.purchase_order.order_number} does not exist'}, status=404)
        
        try:
            product = Product.objects.get(id=order_item.product.id)
            product.quantity += int(quantity)
            product.cost = order_item.unit_cost
            product.save()
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Product with ID: {order_item.product.id} doesn\'t exist'}, status=404)
            
        
        Logs.objects.create(
            purchase_order = purchase_order,
            user= request.user,  #to be removed,
            action= 'stock in',
            product=product,
            quantity=quantity,
            description=f'Stock in from {order_item.purchase_order.order_number}',
            total_quantity=product.quantity 
        )
        
        order_item.receive_items(quantity)
        order_item.check_received()
        
        return JsonResponse({'success': True, 'message': 'Inventory updated successfully'}, status=200)
    
def production_plans(request):
    plans = Production.objects.all().order_by('date_created') 
    return render(request, 'inventory/production_plans.html', {'plans':plans})

def create_production_plan(request):
    
    if request.method == 'POST':
        # Payload
        """
        {
            "cart": [
                {
                    "portions": float,
                    "total_cost": float,
                    "dish": name (str)
                }
            ]
        }
        """
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON data: {e}'}, status=400)
        
        items = data.get('cart')
        
        if not items or not isinstance(items, list):
            return JsonResponse({'success': False, 'message': 'Invalid data: items should be a list'}, status=400)
        
        # Create and save the production plan
        production_plan = Production(status=False, declared=False)
        production_plan.save()
            
        for item in items:
            portions = item.get('portions')
            dish_name = item.get('dish')
            total_cost = item.get('total_cost')
            
            if not portions or not dish_name:
                return JsonResponse({'success': False, 'message': 'Missing data: raw material, quantity, or dish'}, status=400)
            try:
                dish = Dish.objects.get(name=dish_name)
            except Dish.DoesNotExist:
                return JsonResponse({'success': False, 'message': f'Dish with ID: {dish_name} doesn\'t exist'}, status=404)
                  
            
            production_item = ProductionItems.objects.create(
                production=production_plan,
                portions=portions,
                dish=dish,
                total_cost = total_cost,
            )
            
            
        send_production_creation_notification(production_plan.id)
        
        return JsonResponse(
            {
                'success': True, 
                'message': 'Production plan created successfully', 
            }, status=201)
    
    if request.method == 'GET':
        form = ProductionPlanInlineForm()
        return render (request, 'inventory/create_production_plan.html', 
                {
                    'form':form
                }
            )
    return JsonResponse({'success': False, 'message': 'Invalid HTTP method'}, status=405)


def dish_json_detail(request):
    try:
        ingredients = []
        
        data = json.loads(request.body)
        dish_id = data.get("dish_id")
        
        dish = Dish.objects.get(id=dish_id)
        logger.info(dish)
        
        for ingredient in Ingredient.objects.filter(dish=dish):
            if dish == ingredient.dish:
                ingredients.append(
                {
                    'name' : f'{ingredient.raw_material}',
                    'quantity':ingredient.quantity,
                    'cost': ingredient.raw_material.cost
                }
            )
        
        return JsonResponse({'success':True, 'data':ingredients, 'portion_multiplier':dish.portion_multiplier})
    except Dish.DoesNotExist:
        return JsonResponse({'success': False, 'message': f'Dish with ID: {dish_id} doesn\'t exist'}, status=404)

def yeseterdays_left_overs(request):
    # payload
    """
    {
        raw_material:id, 
        dish:id
    }
    """
    
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON data: {e}'}, status=400)
        
        raw_material_id = data.get('raw_material')
        dish_id = data.get('dish')
        
        if not raw_material_id:
            return JsonResponse({'success': False, 'message': 'Missing data: raw material'}, status=400)
        
        if not dish_id:
            return JsonResponse({'success': False, 'message': 'Missing data: Dish'}, status=400)
        
        try:
            raw_material = Product.objects.get(id=raw_material_id)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Raw Material with ID: {raw_material_id} doesn\t exist'}, status=404)
        
        try:
            dish = Dish.objects.get(id=dish_id, major_raw_material=raw_material)
        except Dish.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Dish with ID: {dish_id} doesn\'t exist'}, status=404)
        
        try:
            latest_plan = Production.objects.latest('time_created')
            try:
                latest_production_item = ProductionItems.objects.get(production=latest_plan, raw_material=raw_material, dish=dish)
                logger.info(f'product: {latest_production_item}')
                latest_raw_material_quantity = latest_production_item.remaining_raw_material or 0
                
                latest_left_over_portion_quantity = (latest_production_item.left_overs * latest_production_item.quantity) / \
                                                    (latest_production_item.quantity  * dish.portion_multiplier) or 0
            except ProductionItems.DoesNotExist:
                logger.warning("No Production Items found for the latest plan.")
                latest_raw_material_quantity = 0
                latest_left_over_portion_quantity = 0

        except Production.DoesNotExist:
            logger.warning("No Production Plans found.")
            latest_raw_material_quantity = 0
            latest_left_over_portion_quantity = 0

       
        return JsonResponse(
            {
                'success':True, 
                'data':{
                    'raw_material_dif':float(latest_raw_material_quantity),
                    'left_over_portion_diff':float(latest_left_over_portion_quantity),
                    'unit_cost':float(raw_material.cost),
                    'unit_of_measurement': raw_material.unit.unit_name
                }
            }
        )
           
    return JsonResponse({'success': False, 'message': 'Invalid HTTP method'}, status=405)

def minor_raw_materials(request, pp_id):
    production = Production.objects.get(id=pp_id)
    return render(request, 'inventory/process_minor_raw_materials.html', {'production':production})

def process_raw_materials(request, pp_id):
    production_plan_items = ProductionItems.objects.filter(production__id=pp_id)
    minor_raw_materials = {}
    
    for item in production_plan_items:
        
        for ingredient in Ingredient.objects.filter(dish=item.dish):
            
            if ingredient.raw_material.name in minor_raw_materials:
                
                minor_raw_materials[ingredient.raw_material.name]['quantity'] += ingredient.quantity

            else:
                minor_raw_materials[ingredient.minor_raw_material.name]={
                    'quantity':ingredient.quantity,
                    'cost':ingredient.minor_raw_material.cost,
                    'production_quantity': item.actual_quantity - item.remaining_raw_material
                }
    return JsonResponse(minor_raw_materials)

def confirm_minor_raw_materials(request, pp_id):
    # payload
    """
        [
            "items"{
                'name':{
                    quantity:flaot
                    cost_per_unit:float
                    production_quanity:float
                }
            }
        ]
    """
    try:
        data = json.loads(request.body)
        data =data.get('items')
        raw_material_id = data.get('raw_material_id')
    except Exception as e:
        return JsonResponse({'success':False, 'message':f'{e}'}, status=400)
    try:
        production_plan = Production.objects.get(id=pp_id)
           
        AllocatedRawMaterials.objects.create(
            production = production_plan,
            raw_material = get_object_or_404(Product, id=raw_material_id )
        )
                
        return JsonResponse({'success':True, 'message':f'Production Plan: {production_plan.production_plan_number} Minor Raw Material Successfully Processed .'}, status=200)
    except Exception as e:
        return JsonResponse({'success':False, 'message':f'{e}'}, status=400)

def production_plan_detail(request, pp_id):
    
    if request.method == 'GET':
        try:
            production_plan = Production.objects.get(id=pp_id)
            production_plan_items = ProductionItems.objects.filter(production=production_plan)  
            production_plan_minor_items = MinorProductionItems.objects.filter(production=production_plan)
            
            total_cost_items = production_plan_items.aggregate(total_cost=Sum('total_cost'))['total_cost'] or 0
            total_cost_minor_items = production_plan_minor_items.aggregate(total_cost=Sum('total_cost'))['total_cost'] or 0

            allocated = AllocatedRawMaterials.objects.filter(production=production_plan)
            raw_materials = []
            
            for item in production_plan_items:
                for ing in Ingredient.objects.filter(dish=item.dish):
                    
                    p_r_m_bf, created = ProductionRawMaterials.objects.get_or_create(
                        product=ing.raw_material,
                        defaults = {
                            'quantity':0
                        } 
                    )
                    
                    quantity = ing.quantity * (item.portions / item.dish.portion_multiplier)
                    
                    if len(raw_materials) == 0:
                        raw_materials.append(
                                {
                                    'id':ing.raw_material.id,
                                    'name':ing.raw_material.name,
                                    'quantity_b_f': float(p_r_m_bf.quantity),
                                    'quantity':float(quantity),
                                    'expected_quantity': quantity - p_r_m_bf.quantity
                                }
                            )
                        
                    elif raw_materials[0]['name'] == ing.raw_material.name:
                        raw_materials[0]['quantity'] += quantity
                    else:
                        raw_materials.append(
                            {
                                'id':ing.raw_material.id,
                                'name':ing.raw_material.name,
                                'quantity_b_f': float(p_r_m_bf.quantity),
                                'quantity': float(quantity),
                                'expected_quantity': quantity - p_r_m_bf.quantity
                            }
                        )
                        
        except Exception as e:
            messages.warning(request, f'Production Plan With ID: {pp_id}, doesn\t exists.')
        
        return render(request, 'inventory/confirm_production_plan.html', 
            {
                'production_plan':production_plan,
                'production_plan_items':production_plan_items,
                'production_plan_minor_items':raw_materials,
                'total_cost_items': total_cost_items,
                'total_cost_minor_items': total_cost_minor_items,
                'allocated_rm':allocated,
                'confirm': False
            }
        )

def confirm_production_plan(request, pp_id):
    
    if request.method == 'GET':
        try:
            production_plan = Production.objects.get(id=pp_id)
            production_plan_items = ProductionItems.objects.filter(production=production_plan)
            production_plan_minor_items = MinorProductionItems.objects.filter(production=production_plan)
            total_cost_items = production_plan_items.aggregate(total_cost=Sum('total_cost'))['total_cost'] or 0
            total_cost_minor_items = production_plan_minor_items.aggregate(total_cost=Sum('total_cost'))['total_cost'] or 0
            
            raw_materials = []
            
            for item in production_plan_items:
                for ing in Ingredient.objects.filter(dish=item.dish):
                    
                    p_r_m_bf, created = ProductionRawMaterials.objects.get_or_create(
                        product=ing.raw_material,
                        defaults = {
                            'quantity':0
                        } 
                    )
                    
                    quantity = ing.quantity * (item.portions / item.dish.portion_multiplier)
                    
                    if len(raw_materials) == 0:
                        raw_materials.append(
                                {
                                    'id':ing.raw_material.id,
                                    'name':ing.raw_material.name,
                                    # 'quantity_b_f': float(p_r_m_bf.quantity),
                                    'quantity':float(quantity),
                                    # 'expected_quantity': quantity - p_r_m_bf.quantity
                                }
                            )
                        
                    elif raw_materials[0]['name'] == ing.raw_material.name:
                        raw_materials[0]['quantity'] += quantity
                    else:
                        raw_materials.append(
                            {
                                'id':ing.raw_material.id,
                                'name':ing.raw_material.name,
                                # 'quantity_b_f': float(p_r_m_bf.quantity),
                                'quantity': float(quantity),
                                # 'expected_quantity': quantity - p_r_m_bf.quantity
                            }
                        )
            logger.info(raw_materials)
            
        except Exception as e:
            messages.warning(request, f'{e}')

        return render(request, 'inventory/confirm_production_plan.html', 
            {
                'confirm': True,
                'production_plan':production_plan,
                'production_plan_items':production_plan_items,
                'total_cost_items': total_cost_items,
                'production_plan_minor_items':raw_materials,
            }
        )
        
@transaction.atomic
def process_production_plan_confirmation(request, pp_id):
    try:
        production_plan = Production.objects.select_related().get(id=pp_id)
        production_plan_items = ProductionItems.objects.filter(production=production_plan).select_related('raw_material')
    except Production.DoesNotExist:
        messages.warning(request, f'Production Plan With ID: {pp_id}, doesn\'t exist.')
        return redirect('inventory:process_production_plan', pp_id)
    
    production_plan.status = True
    production_plan.save()
    
    messages.success(request, f'Production plan: {production_plan.production_plan_number.upper()}, successfully confirmed')
    return redirect('inventory:production_plans')


def update_production_plan(request, pp_id):
    if request.method == 'GET':
        form = ProductionPlanInlineForm()
        try:
            production_plan = Production.objects.select_related().get(id=pp_id)
        except Production.DoesNotExist:
            messages.warning(request, f'Production Plan With ID: {pp_id}, doesn\'t exist.')

        return render(request, 'inventory/update_production_plan.html', 
            {
                'form':form,
                'production_plan':production_plan
            }
        )
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON data: {e}'}, status=400)
        
        production_plan_id = data['production_plan_id'] 
            
        try:
            production_plan = Production.objects.select_related().get(id=production_plan_id)
            production_plan_items = ProductionItems.objects.filter(production=production_plan).values(
                'raw_material__name'
                'dish__name'
                'quantity',
                'total_cost', 
                'rm_carried_forward_quantity',
                'lf_carried_forward_quantity',
                'actual_quantity',
                'production_completion_time'
            )
        except Production.DoesNotExist:
            return JsonResponse({'success': False, 'messages': f'Production plan wit ID: {production_plan_id} doesn\'t exists.'})
        
        return JsonResponse(list(production_plan_items), safe=False)


def declare_production_plan(request, pp_id):
    if request.method == 'GET':
        try:
            production_plan = Production.objects.select_related().get(id=pp_id)
            production_plan_items = ProductionItems.objects.filter(production=production_plan)
            allocated_raw_materials = AllocatedRawMaterials.objects.filter(production=production_plan)
          
            raw_materials = []
            
            for item in production_plan_items:
                for ing in Ingredient.objects.filter(dish=item.dish):
                    
                    p_r_m_bf, created = ProductionRawMaterials.objects.get_or_create(
                        product=ing.raw_material,
                        defaults = {
                            'quantity':0.0
                        } 
                    )
                    
                    quantity = ing.quantity * (item.portions / item.dish.portion_multiplier)
                    
                    if len(raw_materials) == 0:
                        raw_materials.append(
                                {
                                    'id':ing.raw_material.id,
                                    'name':ing.raw_material.name,
                                    # 'quantity_b_f': p_r_m_bf.quantity,
                                    'quantity': quantity,
                                    # 'expected_quantity': quantity - p_r_m_bf.quantity
                                }
                            )
                        
                    elif raw_materials[0]['name'] == ing.raw_material.name:
                        raw_materials[0]['quantity'] += quantity
                    else:
                        raw_materials.append(
                            {
                                'id':ing.raw_material.id,
                                'name':ing.raw_material.name,
                                # 'quantity_b_f': float(p_r_m_bf.quantity),
                                'quantity': float(quantity),
                                # 'expected_quantity': quantity - p_r_m_bf.quantity
                            }
                        )
        except Production.DoesNotExist:
            messages.warning(request, f'Production Plan With ID: {pp_id} doesn\'t exist.')
            return redirect('inventory:production_plan_detail', pp_id)
        
        return render(request, 'inventory/declare_raw_material_left.html', {
            'production_plan': production_plan,
            'raw_materials': raw_materials,
            'allocated':allocated_raw_materials 
        })
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON data: {e}'}, status=400)
        
        pp_item_id = data.get('production_plan_item')
        raw_material_used = float(data.get('quantity_used'))
        raw_material_id = data.get('raw_material_id')
        
        if not pp_item_id:
            return JsonResponse({'success': False, 'message': 'Missing Data: Production plan item'}, status=400)
        
        if raw_material_used is None:
            return JsonResponse({'success': False, 'message': 'Missing Data: Raw Material quantity used'}, status=400)
        
        try:
            production= Production.objects.get(id=pp_item_id)
        except ProductionItems.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Production Plan with ID: {pp_item_id} doesn\'t exist'}, status=404)
        
        try:
            allocated = AllocatedRawMaterials.objects.get(raw_material__id=int(raw_material_id), production=production)
        except ProductionItems.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Raw Material with ID: {raw_material_id } doesn\'t exist'}, status=404)

       
        p_rm = ProductionRawMaterials.objects.get(product__id=raw_material_id)
        p_rm.quantity -= raw_material_used
        p_rm.save()
        
        allocated.remaining_quantity = allocated.quantity - raw_material_used
        allocated.save()
        
        return JsonResponse({'success': True}, status=201)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

def production_raw_materials(request):
    raw_materials = ProductionRawMaterials.objects.all()
    # logger.info(raw_materials.values('raw_material__name'))
    return render(request, 'inventory/production_rm.html', {'raw_materials':raw_materials})


def confirm_declaration(request):
    if request.method == 'POST':
        # payload
        """
            production_plan:id (int)
        """
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON data: {e}'}, status=400)
        
        pp_id = data.get('production_plan')
        
        if not pp_id:
            return JsonResponse({'success': False, 'message': 'Missing Data: Production Plan ID'}, status=400)
        
        try:
            production = Production.objects.get(id=pp_id)  
            production_plan_items = ProductionItems.objects.filter(production=production)
            total_cost = production_plan_items.aggregate(total_cost=Sum('total_cost'))['total_cost'] or 0
        except Production.DoesNotExist:
            return JsonResponse({'success':False, 'message':f'Production with ID: {pp_id}, doesn\'t exists'})
        
        declaration_flag = True
        
        COGS.objects.create(
            production=production,
            amount=total_cost
        )
        
        if declaration_flag:
            
            production.declared = True
            production.save()
            
            return JsonResponse(
                {
                    'success':True, 
                    'message':f'Production Plan: {production.production_plan_number} successfully declared'
                }
            )
        else:
            return JsonResponse(
                {
                    'success':False, 
                    'message':f'Production Plan: {production.production_plan_number} declaration failed, Plesase check if you have declared each line'
                }
            )
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

def raw_material_json(request):
    try:
        data = json.loads(request.body)
        raw_material_id = data.get('raw_material_id')
        
        r_m = Product.objects.filter(id=raw_material_id).values('unit__unit_name')
        r_m = list(r_m)
        logger.info(r_m)
        return JsonResponse({'success':True, 'data':r_m})
    except Exception as e:
        return JsonResponse({'success': False, 'message':f'{e}'})
    
    
class DishListView(View):
    def get(self, request):
        dishes = Dish.objects.all()
        ingredients = Ingredient.objects.all()
        logger.info(ingredients)
        return render(request, 'inventory/dish_list.html', 
            {
                'dishes': dishes,
                'ingredients':ingredients
            }
        )
class DishCreateView(View):
    def get(self, request):
        form = DishForm()
        r_m = Product.objects.filter(raw_material=True)
        return render(request, 'inventory/dish_form.html', {'form': form, 'r_m':r_m})

    def post(self, request):
        form = DishForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inventory:dish_list')
        return render(request, 'inventory/dish_form.html', {'form': form})

class DishUpdateView(View):
    
    def get(self, request, pk):
        dish = get_object_or_404(Dish, pk=pk)
        dish_form = DishForm(instance=dish)
        return render(request, 'inventory/dish_form.html', {'dish_form': dish_form, 'dish': dish})

    def post(self, request, pk):
        dish = get_object_or_404(Dish, pk=pk)
        form = DishForm(request.POST, instance=dish)
        if form.is_valid():
            form.save()
            return redirect('inventory:dish_list')
        return render(request, 'inventory/dish_form.html', {'form': form, 'dish': dish})

class DishDeleteView(View):
    
    def get(self, request, pk):
        dish = get_object_or_404(Dish, pk=pk)
        dish.delete()
        return redirect('inventory:dish_list')

# Ingredient Views
class IngredientListView(View):
    
    def get(self, request):
        ingredients = Ingredient.objects.all()
        return render(request, 'inventory/ingredient_list.html', {'ingredients': ingredients})

class IngredientCreateView(View):
    
    def get(self, request):
        form = IngredientForm()
        return render(request, 'inventory/ingredient_form.html', {'form': form})

    def post(self, request):
        form = IngredientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inventory:ingredient_list')
        return render(request, 'inventory/ingredient_form.html', {'form': form})

class IngredientUpdateView(View):
    
    def get(self, request, pk):
        ingredient = get_object_or_404(Ingredient, pk=pk)
        form = IngredientForm(instance=ingredient)
        return render(request, 'inventory/ingredient_form.html', {'form': form, 'ingredient': ingredient})

    def post(self, request, pk):
        ingredient = get_object_or_404(Ingredient, pk=pk)
        form = IngredientForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()
            return redirect('inventory:ingredient_list')
        return render(request, 'inventory/ingredient_form.html', {'form': form, 'ingredient': ingredient})

class IngredientDeleteView(View):
    
    def get(self, request, pk):
        ingredient = get_object_or_404(Ingredient, pk=pk)
        ingredient.delete()
        return redirect('inventory:ingredient_list')

def add_dish(request): # didn't change the name of the template, it caters for both, dish and ingredient creation
    form = IngredientForm()
    dish_form = DishForm()
    
    if request.method == 'GET':
        r_m = Product.objects.filter(raw_material=True)
        return render(request, 'inventory/ingredient_form.html', 
            {
                'r_m':r_m,
                'form':form,
                'dish_form':dish_form
            }
        )
    
    if request.method == 'POST':
        # payload
        """
        {
            name:str
            portion_multiplier:float
            
            "cart": [
                {
                    "name":(str)
                    "raw_material": name (str),
                    "quantity": int,
                    "dish_id": id (int)
                }
            ]
        }
        """
        try:
            
            data = json.loads(request.body)
            cart = data.get('cart')
            logger.info(cart)
            dish_name = data.get('name')
            portion_multiplier = data.get('portion_multiplier')
            
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON data: {e}'}, status=400)
        
        try:
            dish = Dish.objects.create(
                name = dish_name,
                portion_multiplier = portion_multiplier
            )
            
            for item in cart:
                
                raw_material = Product.objects.get(name=item.get('raw_material'))
                
                Ingredient.objects.create(
                    dish=dish,
                    note=item.get('note'),
                    raw_material=raw_material,
                    quantity=item.get('quantity'),
                )

        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}'})
        return JsonResponse({'success':True, 'meessage':f'Ingridient successfully added'})

def meal_list(request):
    meals = Meal.objects.filter(deactivate=False)
    
    return render(request, 'inventory/meal_list.html', 
        {
            'meals':meals,
        }
    )
    
def add_meal(request):
    dishes = Dish.objects.all()
    
    if request.method == 'POST':
        form = MealForm(request.POST)
        
        if form.is_valid():
            name = form.cleaned_data['name']
            price = form.cleaned_data['price']
            
            # validation
            if Meal.objects.filter(name=name).exists():
                messages.warning(request, f'Meal: {name.upper()} exists.')
                return redirect('inventory:add_meal')
            
            if float(price) < 0:
                messages.warning(request, f'Price can\'t be less than zero.')
                return redirect('inventory:add_meal')
            
            form.save()
            messages.success(request, 'Meal successfully added.')
            return redirect('inventory:meal_list')  
    else:
        form = MealForm()
    return render(request, 'inventory/add_meal.html', 
        {
            'dishes':dishes,
            'form': form
        }
    )

def edit_meal(request, meal_id):
    meal = get_object_or_404(Meal, id=meal_id)
    if request.method == 'POST':
        form = MealForm(request.POST, instance=meal)
        if form.is_valid():
            name = form.cleaned_data['name']
            price = form.cleaned_data['price']
            
            # validation
            if float(price) < 0:
                messages.warning(request, f'Price can\'t be less than zero.')
                return redirect('inventory:add_meal')
            
            form.save()
            return redirect('inventory:meal_list')  
    else:
        form = MealForm(instance=meal)

    return render(request, 'inventory/edit_meal.html', 
        {
            'form': form, 
            'meal': meal
        }
    )
    
def delete_meal(request, meal_id):
    try:
        meal = Meal.objects.get(id=meal_id)
        meal.deactivate = True
        meal.save()
        return JsonResponse({'success': True}, status=200)
    except Meal.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Meal does not exist'}, status=400)


def create_meal_category(request):
    if request.method == 'GET':
        categories = MealCategory.objects.all().values()
        logger.info(categories)
        return JsonResponse(list(categories), safe=False)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            category_name = data.get('category')
            
            if category_name:
                category, created = MealCategory.objects.get_or_create(name=category_name)
                if created:
                    return JsonResponse({'success': True, 'id': category.id, 'name': category.name}, status=201)
                else:
                    return JsonResponse({'success': False, 'message': 'Category already exists'}, status=400)
                
            return JsonResponse({'success': False, 'message': 'Invalid data'}, status=405)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'{e}'}, status=400)


def end_of_day_view(request):
    if request.method == 'GET':
        today = localdate()
        
        try:
            e_o_d = EndOfDay.objects.get(date=today)
        except EndOfDay.DoesNotExist:
            e_o_d = None

        # if e_o_d and not e_o_d.done:
        productions_today = Production.objects.filter(date_created=today, status=True, declared=True)
        production_items_today = ProductionItems.objects.filter(production__in=productions_today)

        productions_today = production_items_today.values('dish__name').annotate(
            total_portions=Sum('portions'),
            total_sold=Sum('portions_sold'),
            total_staff_portions=Sum('staff_portions')
        )

        logger.info(productions_today)
        production_data = productions_today
        # else:
        #     production_data = {}

        return render(request, 'end_of_day.html', {
            'date': today,
            'production_today': production_data
        })

    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Get the necessary data
            dish_name = data.get('dish_name')
            total_portions = data.get('total_portions')
            total_sold = data.get('total_sold')
            staff_portions = data.get('total_staff_portions')
            wastage = data.get('wastage')
            leftovers = data.get('leftovers')
            
            
            # production_item = ProductionItems.objects.get(dish__name=dish_name, date=request.POST.get('date'))

            expected = total_portions - total_sold - staff_portions - wastage - leftovers
            
            e_o_d, _ = EndOfDay.objects.get_or_create(
                date=datetime.datetime.today(),
                done = False,
            )
            
            EndOfDayItems.objects.create(
                end_of_day = e_o_d,
                dish_name = data.get('dish_name'),
                total_portions = data.get('total_portions'),
                total_sold = data.get('total_sold'),
                staff_portions = data.get('total_staff_portions'),
                wastage = data.get('wastage'),
                leftovers = data.get('leftovers'),
                expected = expected
            )

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def confirm_end_of_day(request):
    try:
        data = json.loads(request.body)
        amount = data.get('cashed_amount')
        sales = Sale.objects.filter(date=localdate(), staff=False).aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0
        
        e_o_d = EndOfDay.objects.get(date=localdate())
        e_o_d.total_sales = sales
        e_o_d.cashed_amount = Decimal(amount)
        e_o_d.done = True
        e_o_d.save()
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': True})

def supplier_prices(request, raw_material_name):
    """
    {
        raw_material_name: str
    }
    """
    try:

        purchase_orders = PurchaseOrderItem.objects.filter(product__name=raw_material_name)

        supplier_prices = []
        for item in purchase_orders:
            supplier_prices.append(
                {
                    'id':item.purchase_order.supplier.id,
                    'supplier': item.purchase_order.supplier.name, 
                    'price': item.unit_cost
                }
            )

        supplier_prices_sorted = sorted(supplier_prices, key=lambda x: x['price'])
        best_three_prices = supplier_prices_sorted[:3]

        logger.info(best_three_prices)

        return JsonResponse({'success': True, 'suppliers': best_three_prices})

    except Exception as e:
        logger.error(f"Error fetching supplier prices: {e}")
        return JsonResponse({'success': False, 'message': str(e)})


def end_of_day_detail(request, e_o_d_id):
    try:
        end_of_day = EndOfDay.objects.get(id=e_o_d_id)
        end_of_day_items = EndOfDayItems.objects.filter(end_of_day=end_of_day)
        
        total_amount_sold_today = Sale.objects.filter(date=localdate(), staff=False).aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0
        total_amount_staff_sold_today = Sale.objects.filter(date=localdate(), staff=True).aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0
        total_quantity_sold_today = SaleItem.objects.filter(sale__date=localdate(),).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0
        total_staff_portions = SaleItem.objects.filter(sale__date=localdate(), sale__staff=True).aggregate(total_staff_portions=Sum('quantity'))['total_staff_portions'] or 0
        
        logger.info(end_of_day_items)
        
        difference =  end_of_day.cashed_amount - (total_amount_sold_today - total_amount_staff_sold_today) 
        # total_staff_portions= end_of_day_items.objects.aggregate(total_staff_portions=Sum('staff_portions'))['total_staff_portions'] or 0
        
        buffer = generate_end_of_day_report(end_of_day, end_of_day_items, total_amount_staff_sold_today)
        send_end_of_day_report(request, buffer)
        logger.info('email sent')
    except Exception as e:
        messages.warning(request, f'{e}')

    return render(request, 'end_of_day_detail.html', 
        {
            'end_of_day':end_of_day,
            'end_of_day_items':end_of_day_items,
            'total_staff_portions':total_staff_portions,
            'total_amount_sold_today': total_amount_sold_today,
            'total_quantity_sold_today':total_quantity_sold_today,
            'total_amount_staff_sold_today':total_amount_staff_sold_today,
            'non_staff_quantity': total_quantity_sold_today - total_staff_portions,
            'non_staff_total_amount': total_amount_sold_today - total_amount_staff_sold_today,
            'difference': difference
        }
    )
    

def generate_end_of_day_report(end_of_day, items, staff_sold_amount):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    elements = []

    # Title
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'title_style',
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    title = Paragraph(f"End Of Day Report: {end_of_day.date}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Sales Section Title
    sales_title = Paragraph("Sales", styles['Heading2'])
    elements.append(sales_title)
    elements.append(Spacer(1, 6))

    # Sales Section
    sales_data = [
        ["Details", "Quantity", "Amount"],
        ["Total", "", f"{end_of_day.total_sales:.2f}"],
        ["Staff", "", "(6.00)"],
        ["Non Staff", "", f"{end_of_day.total_sales - 6:.2f}"],
        ["Cashed Amount", "", f"{end_of_day.cashed_amount:.2f}"],
        ["Difference", "", f"{end_of_day.cashed_amount - (end_of_day.total_sales - staff_sold_amount):.2f}"],
    ]

    sales_table = Table(sales_data, colWidths=[2 * inch, 1 * inch, 2 * inch])
    sales_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Align the entire table to the left
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(sales_table)
    elements.append(Spacer(1, 12))

    # Dishes Section Title
    dishes_title = Paragraph("Dishes", styles['Heading2'])
    elements.append(dishes_title)
    elements.append(Spacer(1, 6))

    # Dishes Section
    dish_data = [
        ["Dish Name", "S A C Portions", "P Sold", "S Portions", "Price Per Unit", "Wastage", "Left Overs", "Over/Less"]
    ]
    for item in items:
        dish_data.append([
            item.dish_name,
            item.total_portions,
            item.total_sold,
            item.staff_portions,
            "N/A",  
            item.wastage,
            item.leftovers,
            item.expected
        ])

    dish_table = Table(dish_data, colWidths=[1 * inch] * 8)
    dish_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(dish_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

def send_end_of_day_report(request, buffer):
    email = EmailMessage(
        f"End of Day Report:",
        "Please find the attached End of Day report. The expected amount is to be calculated on cost price, since they are no stipulated prices per dishes, but if they to be put the expected table will be relavant.",
        'admin@techcity.co.zw',
        ['cassymyo@gmail.com'],
    )
    email.attach(f'EndOfDayReport.pdf', buffer.getvalue(), 'application/pdf')
    
    # Run email sending in a thread
    EmailThread(email).start()

    logger.info(f' End of day report email sent.')
    
def confirm_minor_raw(request):
    # payload 
    """
        {
            raw_material_id: float
            quantity:float
        }
    """
    try:
        data = json.loads(request.body)
        
        raw_material_id = data.get('raw_material_id')
        quantity = data.get('quantity')
        production_id = data.get('production_id')
        quantity = float(quantity)
        
        logger.info(quantity)
        raw_material = Product.objects.get(id=raw_material_id)
        
        production = Production.objects.get(id=production_id)
        
        p_raw_materials, created = ProductionRawMaterials.objects.get_or_create(
            product = raw_material,
            
            defaults={
                "quantity":quantity,
                "quantity_left":0.0
            }  
        )
        
        AllocatedRawMaterials.objects.create(
            production = production,
            raw_material = raw_material,
            quantity = quantity
        )
        
        p_raw_materials.quantity += quantity
        p_raw_materials.save()
        
        raw_material.quantity -= quantity
        raw_material.save()
        
        logger.info(raw_material.quantity)
        
        Logs.objects.create(
            user=request.user, 
            action= 'Transfer',
            description='to production',
            product=raw_material,
            quantity=quantity,
            total_quantity=raw_material.quantity,
        )
        
        if not raw_material_id or not quantity:
            return JsonResponse({'success':False, 'message':'Missin Data: Raw Material or Quantity'}, status=400)
    except Exception as e:
        return JsonResponse({'success':False, 'message':f'{e}'}, status=400)
    return JsonResponse({'success':True}, status=200)


@login_required
def calculate_reorder_point(product):
    average_weekly_usage = product.average_daily_usage * 7
    lead_time_in_weeks = product.lead_time / 7
    reorder_point = (average_weekly_usage * lead_time_in_weeks) + product.safety_stock
    return reorder_point




