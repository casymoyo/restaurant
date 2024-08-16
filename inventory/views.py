import json
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

from finance.models import (
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


# to be removed
User = get_user_model()

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
    
    raw_materials = Product.objects.filter(raw_material=True, quantity__gt=0)
    finished_products = Product.objects.filter(raw_material=False)
    logger.info(finished_products)
    return render(request, 'inventory/products.html', 
        {
            'raw_materials':raw_materials,
            'finished_products':finished_products
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
            user=user.objects.get(id=1), #to be removed
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
                    quantity = int(item_data['quantity'])
                    unit_cost = Decimal(item_data['price'])

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
                        received=False
                    )

                    # consider to put expenses
                if purchase_order.status == 'received':
                    category, _ = ExpenseCategory.objects.get_or_create(
                        name = 'Inventory'
                    )
                    
                    expense = Expense.objects.create(
                        category = category,
                        amount = purchase_order.total_cost,
                        user = User.objects.get(id=1),
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
                    user = User.objects.get(id=1),
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

# @login_required
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
    
# @login_required
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
            user= User.objects.get(id=1),  #to be removed,
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
    plans = Production.objects.all().order_by('-date_created') 
    return render(request, 'inventory/production_plans.html', {'plans':plans})


def create_production_plan(request):
    
    if request.method == 'POST':
        # Payload
        """
        {
            "cart": [
                {
                    "raw_material": name (str),
                    "quantity": int,
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
            raw_material_name = item.get('raw_material')
            quantity = item.get('quantity')
            dish_name = item.get('dish')
            # rm_cf_quantity = item.get('rm_bf_quantity')
            # lf_cf_quantity = item.get('lf_bf_quantity')
            actual_quantity = item.get('actual_quantity')
            pct = item.get('timeout')
            total_cost = item.get('total_cost')
            
            if not raw_material_name or not quantity or not dish_name:
                return JsonResponse({'success': False, 'message': 'Missing data: raw material, quantity, or dish'}, status=400)
            
            try:
                raw_material = Product.objects.get(name=raw_material_name)
            except Product.DoesNotExist:
                return JsonResponse({'success': False, 'message': f'Raw Material with ID: {raw_material_name} doesn\'t exist'}, status=404)
                
            try:
                dish = Dish.objects.get(name=dish_name)
            except Dish.DoesNotExist:
                return JsonResponse({'success': False, 'message': f'Dish with ID: {dish_name} doesn\'t exist'}, status=404)
            
            if (quantity - actual_quantity) >= 0:
                logger.info(f'here:')
                rm_cf_quantity = 0
                lf_cf_quantity = 0
                
            
            production_item = ProductionItems.objects.create(
                production=production_plan,
                raw_material=raw_material,
                quantity=quantity,
                dish=dish,
                rm_carried_forward_quantity=rm_cf_quantity,
                lf_carried_forward_quantity=lf_cf_quantity,
                actual_quantity=actual_quantity,
                production_completion_time=pct,
                total_cost = total_cost
            )
            logger.info(f'{production_item} : Saved successfully')
        
        return JsonResponse({'success': True, 'message': 'Production plans created successfully'}, status=201)
    
    if request.method == 'GET':
        form = ProductionPlanInlineForm()
        return render (request, 'inventory/create_production_plan.html', 
                {
                    'form':form
                }
            )
    return JsonResponse({'success': False, 'message': 'Invalid HTTP method'}, status=405)


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
            dish = Dish.objects.get(id=dish_id, raw_material=raw_material)
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

def production_plan_detail(request, pp_id):
    
    if request.method == 'GET':
        try:
            production_plan = Production.objects.get(id=pp_id)
            production_plan_items = ProductionItems.objects.filter(production=production_plan)
        except Exception as e:
            messages.warning(request, f'Production Plan With ID: {pp_id}, doesn\t exists.')
        
        return render(request, 'inventory/confirm_production_plan.html', 
            {
                'production_plan':production_plan,
                'production_plan_items':production_plan_items,
                'confirm': False
            }
        )

def confirm_production_plan(request, pp_id):
    
    if request.method == 'GET':
        try:
            production_plan = Production.objects.get(id=pp_id)
            production_plan_items = ProductionItems.objects.filter(production=production_plan)
        except Exception as e:
            messages.warning(request, f'Production Plan With ID: {pp_id}, doesnt exists.')
        
        logger.info(production_plan_items)
        return render(request, 'inventory/confirm_production_plan.html', 
            {
                'production_plan':production_plan,
                'production_plan_items':production_plan_items,
                'confirm': True
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
    
    # Update production plan status
    production_plan.status = True
    production_plan.save()
    
    # Process each item in the production plan
    for item in production_plan_items:
        try:
            raw_material = item.raw_material
        except Product.DoesNotExist:
            messages.warning(request, f'Raw Material with name: {item.raw_material.name}, doesn\'t exist.')
            return redirect('inventory:process_production_plan', pp_id)
        
        raw_material.quantity -= item.actual_quantity
        raw_material.save()  
        item.save()
    
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
            production_plan_items = ProductionItems.objects.filter(production=production_plan).select_related('raw_material')
        except Production.DoesNotExist:
            messages.warning(request, f'Production Plan With ID: {pp_id} doesn\'t exist.')
            return redirect('inventory:production_plan_detail', pp_id)
        
        return render(request, 'inventory/declare_raw_material_left.html', {
            'production_plan': production_plan,
            'production_plan_items': production_plan_items,
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON data: {e}'}, status=400)
        
        pp_item_id = data.get('production_plan_item')
        raw_material_used = data.get('quantity_used')
        portions =  data.get('portions')
        
        if not pp_item_id:
            return JsonResponse({'success': False, 'message': 'Missing Data: Production plan item'}, status=400)
        
        if raw_material_used is None:
            return JsonResponse({'success': False, 'message': 'Missing Data: Raw Material quantity used'}, status=400)
        
        try:
            production_plan_item = ProductionItems.objects.get(id=pp_item_id)
        except ProductionItems.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Production Plan Item with ID: {pp_item_id} doesn\'t exist'}, status=404)

        production_plan_item.remaining_raw_material = production_plan_item.actual_quantity - raw_material_used
        production_plan_item.declared = True
        production_plan_item.portions = int(portions)
        production_plan_item.save()
        
        logger.info(f'Production plan line: {production_plan_item.raw_material.name} successfully saved')
        
        return JsonResponse({'success': True}, status=201)

    else:
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

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
            production_plan_item = ProductionItems.objects.filter(production=production)
            logger.info(f"Production item: {production_plan_item}")
        except Production.DoesNotExist:
            return JsonResponse({'success':False, 'message':f'Production with ID: {pp_id}, doesn\'t exists'})
        
        declaration_flag = True
        
        for item in production_plan_item:
            if item.declared == False:
                declaration_flag = False
                break
        
        if declaration_flag:
            
            production.declared =True
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
        return render(request, 'inventory/dish_form.html', {'form': form})

    def post(self, request):
        form = DishForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inventory:dish_list')
        return render(request, 'inventory/dish_form.html', {'form': form})

class DishUpdateView(View):
    
    def get(self, request, pk):
        dish = get_object_or_404(Dish, pk=pk)
        form = DishForm(instance=dish)
        return render(request, 'inventory/dish_form.html', {'form': form, 'dish': dish})

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


def add_ingredient(request, dish_id):
    form = IngredientForm()
    
    if request.method == 'GET':
        
        dish = Dish.objects.get(id=dish_id)
        
        return render(request, 'inventory/ingredient_form.html', 
            {
                'dish':dish,
                'form':form
            }
        )
    
    if request.method == 'POST':
        # payload
        """
        {
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
            dish_id = data.get('dish_id')
            
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON data: {e}'}, status=400)
        
        try:
            dish = Dish.objects.get(id=dish_id)
            
            for item in cart:
                name =item.get('raw_material')
                raw_material = Product.objects.get(name=item.get('raw_material'))
                logger.info(name)
                Ingredient.objects.create(
                    dish=dish,
                    name=item.get('name'),
                    raw_material=raw_material,
                    quantity=int(item.get('quantity')),
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
            if Meal.objects.filter(name=name).exists():
                messages.warning(request, f'Meal: {name.upper()} exists.')
                return redirect('inventory:add_meal')
            
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
    
    latest_plan = Production.objects.latest('time_created')

    ProductionItemsFormSet = modelformset_factory(ProductionItems, fields=('dish', 'portions', 'wastage', 'left_overs', 'portions_sold'), extra=0)

    if request.method == 'POST':
        formset = ProductionItemsFormSet(request.POST, queryset=ProductionItems.objects.filter(production=latest_plan))

        if formset.is_valid():
            formset.save()
            return redirect(reverse('end_of_day_view'))

    else:
        formset = ProductionItemsFormSet(queryset=ProductionItems.objects.filter(production=latest_plan))

    return render(request, 'end_of_day.html', {'formset': formset, 'latest_plan': latest_plan})
