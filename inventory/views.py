import json, csv, io
from django.utils import timezone
from . models import *
from loguru import logger
from decimal import Decimal
from django.views import View    
from django.contrib import messages 
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from loguru import logger
from .models import Dish, Ingredient
from django.views import View
from django.db.models import Sum
from django.utils.timezone import localdate
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from utils.email import EmailThread
from django.core.mail import EmailMessage
from finance.models import COGS
from datetime import timedelta
import datetime

from finance.models import (
    Sale,
    SaleItem,
    CashBook,
    Expense, 
    CashUp,
    ExpenseCategory
)
from .tasks import (
    send_production_creation_notification,
    transfer_notification,
    supplier_email
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
    IngredientForm,
    TransferForm
)

from utils.supplier_best_price import best_price

@login_required
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
                return JsonResponse({'success':False, 'message':f'Unit of Measurement with the name {unit_name} exists'}, status=400)
            
            unit_obj = UnitOfMeasurement(
                unit_name=unit_name
            )
            unit_obj.save()
            logger.info(f'{unit_obj.unit_name}, successfully created')
            return JsonResponse({'success':True}, status=200)
        
        return JsonResponse({'success':False, 'message':'Unit of measurement is invalid'}, status=400)
    
    return JsonResponse({'success':False, 'message':'Invalid request'}, status=400)
                  

@login_required
def products(request):
    raw_materials = Product.objects.filter()
    return render(request, 'inventory/products.html', 
        {
            'raw_materials':raw_materials,
            'count':raw_materials.count()
        }
    )
    

@login_required
def inventory(request):
    product_name = request.GET.get('name', '')
    if product_name:
        
        return JsonResponse(list(Product.objects.filter(name=product_name).values(
                'unit__unit_name',
                'name',
                'id'
            )), safe=False)
    return JsonResponse({'error':'product doesnt exists'})


@login_required
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


@login_required
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


@login_required
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

@login_required
def production_rm_detail(request, rm_id):
    try: 
        product = ProductionRawMaterials.objects.get(id=rm_id)
        logger.info(product)
    except Product.DoesNotExist:
        messages.warning(request, f'Product with ID: {rm_id} doesn\'t exists')
        
    logs = ProductionLogs.objects.filter(product=product)

    return render(request, 'inventory/production_rm_detail.html', 
        {
            'product': product,
            'logs': logs,
        }
    )
    
    
@login_required
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
            action= 'Stock update',
            product=product,
            quantity=request.POST['quantity'],
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
    

@login_required
def suppliers(request):
    form = AddSupplierForm()
    suppliers = Supplier.objects.all()
    return render(request, 'inventory/suppliers.html', 
        {
            'suppliers':suppliers,
            'form':form
        }
    )
    

@login_required
def supplier_list_json(request):
    suppliers = Supplier.objects.all().values(
        'id',
        'name'
    )
    return JsonResponse(list(suppliers), safe=False)


@login_required
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
    
        
@login_required
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


@login_required
def purchase_orders(request):
    form = CreateOrderForm()
    status_form = PurchaseOrderStatus()
    orders = PurchaseOrder.objects.filter().order_by('-order_date')
    return render(request, 'inventory/purchase_orders.html', 
        {
            'form':form,
            'orders':orders,
            'status_form':status_form 
        }
    )
      
@login_required
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

                    purchase_order_item = PurchaseOrderItem.objects.create(
                        purchase_order=purchase_order,
                        product=product,
                        quantity=quantity,
                        unit_cost=unit_cost,
                        received_quantity=0,
                        received=False,
                        note=note
                    )

                    supplier_email(purchase_order.supplier.id, purchase_order_item)

                # consider to put expenses
                if purchase_order.status == 'received': 
                    category, _ = ExpenseCategory.objects.get_or_create(
                        name = 'Inventory'
                    )
                    
                    expense = Expense.objects.create(
                        category = category,
                        amount = purchase_order.total_cost,
                        user = request.user,
                        description = f'Purchase order{purchase_order.order_number}',
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

    
@login_required
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


@login_required
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
    

@login_required
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
    
    
@login_required
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
        purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order)
    except PurchaseOrder.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} doesn\'t exists')
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
            order_item_id = data.get('id')
            quantity = int(data.get('quantity', 0))

            if not order_item_id or quantity <= 0:
                return JsonResponse({'success': False, 'message': 'Invalid data'}, status=400)

            order_item = PurchaseOrderItem.objects.select_related('purchase_order', 'product').get(id=order_item_id)
            
            if (quantity + order_item.received_quantity) > order_item.quantity:
                return JsonResponse({'success': False, 'message': 'Quantity received cannot be more.'})
             
            purchase_order = order_item.purchase_order
            product = order_item.product

            product.quantity += quantity
            product.cost = order_item.unit_cost
            product.save()

            Logs.objects.create(
                purchase_order=purchase_order,
                user=request.user, 
                action='stock in',
                product=product,
                quantity=quantity,
                description=f'Stock in from {purchase_order.order_number}',
                total_quantity=product.quantity
            )

            order_item.receive_items(quantity)
            order_item.check_received()

            return JsonResponse({'success': True, 'message': 'Inventory updated successfully'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON payload'}, status=400)
        except PurchaseOrderItem.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Purchase Order Item not found'}, status=404)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)


@login_required   
def production_plans(request):
    
    plans = Production.objects.all().order_by('date_created') 
    transfer_count = Transfer.objects.filter(status=False).count()
    
    return render(request, 'inventory/production_plans.html', {'plans':plans, 'transfer_count':transfer_count})

@login_required
@transaction.atomic
def create_production_plan(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON data: {e}'}, status=400)

        items = data.get('cart', [])
        if not items or not isinstance(items, list):
            return JsonResponse({'success': False, 'message': 'Invalid data: items should be a list'}, status=400)

        if Production.objects.filter(declared=False).exists():
            return JsonResponse({'success': False, 'message': 'Please declare all the production plans you have.'}, status=400)

        # Create a new production plan
        production_plan = Production.objects.create(status=False, declared=False)

        dish_names = [item.get('dish') for item in items if item.get('dish')]
        dishes = Dish.objects.filter(name__in=dish_names)
        dish_map = {dish.name: dish for dish in dishes}

        if len(dish_map) != len(dish_names):
            return JsonResponse({'success': False, 'message': 'Some dishes do not exist'}, status=404)

        production_items = []
        raw_materials_to_checklist = set()

        for item in items:
            portions = item.get('portions')
            dish_name = item.get('dish')
            total_cost = item.get('total_cost')

            if not portions or not dish_name:
                return JsonResponse({'success': False, 'message': 'Missing data: portions or dish'}, status=400)

            dish = dish_map.get(dish_name)

            if dish is None:
                return JsonResponse({'success': False, 'message': f'Dish {dish_name} does not exist'}, status=404)

            ingredients = Ingredient.objects.filter(dish=dish).select_related('raw_material')

            # Add production item to the list for bulk creation
            production_items.append(ProductionItems(
                production=production_plan,
                portions=portions,
                dish=dish,
                total_cost=total_cost,
                allocated=False
            ))

            # Collect raw materials for checklist creation
            for ingredient in ingredients:
                raw_materials_to_checklist.add(ingredient.raw_material)

        # Bulk create production items to reduce the number of queries
        ProductionItems.objects.bulk_create(production_items)

        today = datetime.datetime.today()
        existing_checklists = set(CheckList.objects.filter(date=today, product__in=raw_materials_to_checklist)
                                  .values_list('product_id', flat=True))

        new_checklists = [
            CheckList(product=raw_material, status=False)
            for raw_material in raw_materials_to_checklist
            if raw_material.id not in existing_checklists
        ]
        CheckList.objects.bulk_create(new_checklists)

        send_production_creation_notification(production_plan.id)

        return JsonResponse({'success': True, 'message': 'Production plan created successfully'}, status=201)

    elif request.method == 'GET':
        form = ProductionPlanInlineForm()
        return render(request, 'inventory/create_production_plan.html', {'form': form})

    return JsonResponse({'success': False, 'message': 'Invalid HTTP method'}, status=405)


@login_required
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


@login_required
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


@login_required
def minor_raw_materials(request, pp_id):
    production = Production.objects.get(id=pp_id)
    return render(request, 'inventory/process_minor_raw_materials.html', {'production':production})


@login_required
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


@login_required
def confirm_minor_raw_materials(request, pp_id):
    # payload
    """
        [
            "items"{
                'name':{
                    quantity:flaot
                    cost_per_unit:float
                    production_quantity:float
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
        # production_item = ProductionItem.objects.get(production=production_plan, )
        AllocatedRawMaterials.objects.create(
            production = production_plan,
            raw_material = get_object_or_404(Product, id=raw_material_id )
        )
                
        return JsonResponse({'success':True, 'message':f'Production Plan: {production_plan.production_plan_number} Minor Raw Material Successfully Processed .'}, status=200)
    except Exception as e:
        return JsonResponse({'success':False, 'message':f'{e}'}, status=400)


@login_required
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
                    # Fetch or create ProductionRawMaterials instance
                    p_r_m_bf, created = ProductionRawMaterials.objects.get_or_create(
                        product=ing.raw_material,
                        defaults={'quantity': 0}
                    )

                    required_quantity = ing.quantity * (item.portions / item.dish.portion_multiplier)

                    production_inventory = ProductionRawMaterials.objects.filter(product=ing.raw_material).first()
                    current_quantity = production_inventory.quantity if production_inventory else 0

                    expected_quantity = required_quantity - current_quantity

                    raw_material_found = next((rm for rm in raw_materials if rm['id'] == ing.raw_material.id), None)
                    
                    if raw_material_found:
                     
                        raw_material_found['quantity'] += required_quantity
                        raw_material_found['expected_quantity'] += expected_quantity
                        raw_material_found['quantity_b_f'] += current_quantity
                    else:
                        
                        raw_materials.append(
                            {
                                'id': ing.raw_material.id,
                                'name': ing.raw_material.name,
                                'quantity_b_f': float(current_quantity),
                                'quantity': float(required_quantity),
                                'expected_quantity': float(expected_quantity),
                            }
                        )
                        
        except Exception as e:
            messages.warning(request, f'Production Plan With ID: {pp_id}, doesn\t exists.')
        
        return render(request, 'inventory/production_plan_detail.html', 
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
 

@login_required       
def confirm_production_plan(request, pp_id):
    if request.method == 'GET':
        try:
            production_plan = Production.objects.get(id=pp_id)
            production_plan_items = ProductionItems.objects.filter(production=production_plan)
            total_cost_items = production_plan_items.aggregate(total_cost=Sum('total_cost'))['total_cost'] or 0

            raw_materials = []
            
            for item in production_plan_items:
                for ing in Ingredient.objects.filter(dish=item.dish):
                   
                    p_r_m_bf, created = ProductionRawMaterials.objects.get_or_create(
                        product=ing.raw_material,
                        defaults={'quantity': 0}
                    )

                    required_quantity = ing.quantity * (item.portions / item.dish.portion_multiplier)

                    production_inventory = ProductionRawMaterials.objects.filter(product=ing.raw_material).first()
                    current_quantity = production_inventory.quantity if production_inventory else 0

                    expected_quantity = required_quantity - current_quantity

                    raw_material_found = next((rm for rm in raw_materials if rm['id'] == ing.raw_material.id), None)
                    
                    if raw_material_found:
                        raw_material_found['quantity'] += required_quantity
                        raw_material_found['expected_quantity'] += expected_quantity
                        raw_material_found['quantity_b_f'] += current_quantity
                    else:
                        raw_materials.append(
                            {
                                'id': ing.raw_material.id,
                                'name': ing.raw_material.name,
                                'quantity_b_f': float(current_quantity),
                                'quantity': float(required_quantity),
                                'expected_quantity': float(expected_quantity),
                            }
                        )
            logger.info(raw_materials)
            
        except Exception as e:
            messages.warning(request, f'{e}')

        return render(request, 'inventory/confirm_production_plan.html', 
            {
                'confirm': True,
                'production_plan': production_plan,
                'production_plan_items': production_plan_items,
                'total_cost_items': total_cost_items,
                'production_plan_minor_items': raw_materials,
            }
        )


@login_required      
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


@login_required
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


@login_required
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
                        defaults={
                            'quantity': 0
                        } 
                    )
                    
                    quantity = ing.quantity * (item.portions / item.dish.portion_multiplier)
                    
                    raw_material_found = next((rm for rm in raw_materials if rm['id'] == ing.raw_material.id), None)
                    
                    if raw_material_found:
                        
                        raw_material_found['quantity'] += quantity
                    else:
                        
                        raw_materials.append(
                            {
                                'id': ing.raw_material.id,
                                'name': ing.raw_material.name,
                                'quantity': float(quantity),
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
            
            
            allocated.remaining_quantity = allocated.quantity - raw_material_used
            allocated.save()
            
            ProductionLogs.objects.create(
                user=request.user, 
                action= 'declared',
                description='from warehouse',
                product=p_rm,
                quantity=p_rm.quantity,
                total_quantity=p_rm.quantity,
            )
            p_rm.save()
            
            return JsonResponse({'success': True}, status=201)
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON data: {e}'}, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)


@login_required
def production_raw_materials(request):
    raw_materials = ProductionRawMaterials.objects.all()
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


@login_required
def raw_material_json(request):
    try:
        data = json.loads(request.body)
        raw_material_id = data.get('raw_material_id')
        
        r_m = Product.objects.filter(id=raw_material_id).values(
            'cost',
            'unit__unit_name'
        )
        r_m = list(r_m)
    
        return JsonResponse({'success':True, 'data':r_m})
    except Exception as e:
        return JsonResponse({'success': False, 'message':f'{e}'})
    
    
class DishListView(View):
    def get(self, request):
        dishes = Dish.objects.all()
        ingredients = Ingredient.objects.all()

        # if download:
        #     logger.info('download')
        #     response = HttpResponse(content_type='text/csv')
        #     response['Content-Disposition'] = f'attachment; filename="_{filter_option}.csv"'

        #     writer = csv.writer(response)
        #     writer.writerow(['Date', 'Description', 'Done By', 'Amount'])

        #     total_expense = 0  
        #     for expense in expenses:
        #         total_expense += expense.amount

        #         writer.writerow([
        #             expense.date,
        #             expense.description,
        #             expense.user.first_name,
        #             expense.amount,
        #         ])

        #     writer.writerow(['Total', '', '', total_expense])
        
            # return response
        return render(request, 'inventory/dish_list.html', 
            {
                'dishes': dishes,
                'ingredients':ingredients
            }
        )
    
# to remove
def p_home(request):
    return render(request, 'inventory/production_home.html')
    
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
    

@login_required
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
            cost:float
            category:str
            
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
        
            dish_name = data.get('name')
            portion_multiplier = data.get('portion_multiplier')
            cost = data.get('dish_cost')
            selling_price = data.get('selling_price')
            category = data.get('category')

            if not dish_name or not portion_multiplier or not cost or not selling_price:
                return JsonResponse({'success': False, 'message': f'Please fill all the missing data'}, status=400)
            
            with transaction.atomic():
 
                dish = Dish.objects.create(
                    cost = cost,
                    name = dish_name,
                    portion_multiplier = portion_multiplier,
                    price = selling_price,
                    category=category
                )
                
                """if category exists in meal category return else create and assign to the dish"""
                category, _ =  MealCategory.objects.get_or_create(name=dish.name)

                meal = Meal.objects.create(
                    name=dish.name,
                    price=dish.price,
                    category=category,
                    deactivate=False
                )
                
                meal.dish.set([dish])
                meal.save()

                for item in cart:
                    raw_material = Product.objects.get(name=item.get('raw_material'))
                    Ingredient.objects.create(
                        dish=dish,
                        note=item.get('note'),
                        raw_material=raw_material,
                        quantity=item.get('quantity'),
                    )

        except Exception as e:
            logger.info(e)
            return JsonResponse({'success':False, 'message':f'{e}'})
        return JsonResponse({'success':True, 'meessage':f'Ingridient successfully added'})


@login_required
def meal_list(request):
    meals = Meal.objects.filter(deactivate=False)
    
    return render(request, 'inventory/meal_list.html', 
        {
            'meals':meals,
        }
    )


@login_required  
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

@login_required
def get_dish_data(request, dish_id):
    try:
        dish = Dish.objects.filter(id=dish_id).values(
            'name',
            'cost',
            'price',
            'category',
            'portion_multiplier'
        )
        ingredients =Ingredient.objects.filter(dish__id = dish_id).values(
            'note',
            'quantity',
            'raw_material__name',
            'raw_material__cost'
        )

        return JsonResponse({'success':True, 'dish':list(dish), 'ingridients':list(ingredients)})

    except Exception as e:
        return JsonResponse({'success':False, 'message':f'{e}'})

@login_required
def edit_dish(request, dish_id):
    if request.method == 'GET':
        try:
            dish = Dish.objects.get(id=dish_id)
            dish_form = DishForm()
            r_m = Product.objects.filter(raw_material=True)

            return render(request, 'inventory/edit_dish.html',{
                'r_m':r_m,
                'dish':dish,
                'dish_form': dish_form
            })
        except:
            return JsonResponse({'success':False, 'message':f'Dish not found'})
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cart = data.get('cart', [])
            
            logger.info(f'cart: {cart}')
            
            dish_name = data.get('name')
            portion_multiplier = data.get('portion_multiplier')
            cost = data.get('dish_cost')
            selling_price = data.get('selling_price')
            category = data.get('category')


            cat, _= MealCategory.objects.get_or_create(name=category) 
            dish = Dish.objects.get(id=dish_id)
            logger.info(f'Dish name: {dish_name}')
            dish.name = dish_name
            dish.portion_multiplier = portion_multiplier
            dish.cost = cost
            dish.price = selling_price
            dish.category = dish.category
            existing_ingredients = Ingredient.objects.filter(dish=dish)
            existing_ingredient_names = {ing.raw_material.name for ing in existing_ingredients}
            raw_material_map = {rm.name: rm for rm in Product.objects.all()}

            ingredient_updates = []
            ingredients_to_delete = existing_ingredients[:]

            for item in cart:
                raw_material_name = item['raw_material']
                raw_material = raw_material_map.get(raw_material_name)

                if not raw_material:
                    return JsonResponse({'success': False, 'message': f'Raw material "{raw_material_name}" not found.'})

                if raw_material_name in existing_ingredient_names:
                    ing = next(ing for ing in existing_ingredients if ing.raw_material.name == raw_material_name)
                    ing.quantity = item['quantity']
                    ing.note = item['note']
                    ingredient_updates.append(ing)

                    ingredients_to_delete.remove(ing)
                else:
                    ingr = Ingredient.objects.create(
                        dish=dish,
                        raw_material=raw_material,
                        quantity=item['quantity'],
                        note=item['note'],
                    )
                    logger.info(f'Added ingredient: {ingr}')

            if ingredients_to_delete:
                logger.info(f'Deleting ingredients: {ingredients_to_delete}')
                Ingredient.objects.filter(id__in=[ing.id for ing in ingredients_to_delete]).delete()

            if ingredient_updates:
                logger.info(f'Updating ingredients: {ingredient_updates}')
                with transaction.atomic():
                    Ingredient.objects.bulk_update(ingredient_updates, fields=['quantity', 'note'])

            dish.save()
            return JsonResponse({'success': True}, status=200)

        except Exception as e:
            logger.error(f'Error processing request: {e}')
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        
    return JsonResponse({'success':False, 'message':'Invalid request'}, status=500)

@login_required
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


@login_required
def delete_meal(request, meal_id):
    try:
        meal = Meal.objects.get(id=meal_id)
        meal.deactivate = True
        meal.save()
        return JsonResponse({'success': True}, status=200)
    except Meal.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Meal does not exist'}, status=400)



@login_required
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

@login_required
def end_of_day_view(request):
    if request.method == 'GET':
        today = localdate()
        
        try:
            e_o_d = EndOfDay.objects.get(date=today)
        except EndOfDay.DoesNotExist:
            e_o_d = None

        productions_today = Production.objects.filter(date_created=today, status=True, declared=True)
        production_items_today = ProductionItems.objects.filter(production__in=productions_today)

        productions_today = production_items_today.values('dish__name').annotate(
            total_portions=Sum('portions'),
            total_sold=Sum('portions_sold'),
            total_staff_portions=Sum('staff_portions')
        )

        production_data = productions_today
       

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
            
            e_o_d_obj = EndOfDayItems.objects.create(
                end_of_day = e_o_d,
                dish_name = data.get('dish_name'),
                total_portions = data.get('total_portions'),
                total_sold = data.get('total_sold'),
                staff_portions = data.get('total_staff_portions'),
                wastage = data.get('wastage'),
                leftovers = data.get('leftovers'),
                expected = expected
            )
            
            dish = Dish.objects.get(name=dish_name)
            
            ingredient_with_max_quantity = Ingredient.objects.all().order_by('-quantity').first()
            
            if ingredient_with_max_quantity:
                logger.info(f"The ingredient with the greatest quantity is: {ingredient_with_max_quantity.raw_material}")
                kgs_left = e_o_d_obj.leftovers / dish.portion_multiplier 
                
                prod_rm = ProductionRawMaterials.objects.get(product=ingredient_with_max_quantity.raw_material)
                prod_rm.quantity += kgs_left
                prod_rm.save()
            else:
                return JsonResponse({'success': False, 'message': "No ingredients found."})
        
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)


@login_required
@transaction.atomic
def confirm_end_of_day(request):
    try:
        data = json.loads(request.body)
        amount = data.get('cashed_amount')
        sales = Sale.objects.filter(date=localdate(), staff=False).aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0
        total_amount_staff_sold_today = Sale.objects.filter(date=localdate(), staff=True).aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0
        
        e_o_d = EndOfDay.objects.get(date=localdate())
        e_o_d.total_sales = sales
        e_o_d.cashed_amount = Decimal(amount)
        e_o_d.done = True
        e_o_d.save()

        end_of_day_items = EndOfDayItems.objects.filter(end_of_day=e_o_d)
        
        # create cash in object
        CashUp.objects.create(
            cashier = request.user,
            cashed_amount = amount,
            sales = sales,
            user = request.user, 
            status = True if amount == sales else False
        )

        buffer = generate_end_of_day_report(e_o_d, end_of_day_items, total_amount_staff_sold_today)
        logger.info(f'buffer: {buffer}')
        send_end_of_day_report(request, buffer)
        
        logger.info('saved')
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': True})


@login_required
def supplier_prices(request, raw_material_name):
    """
        {
            raw_material_name: str
        }
    """
    try:
        
        best_three_prices = best_price(raw_material_name)
        logger.info(best_three_prices)
        return JsonResponse({'success': True, 'suppliers': best_three_prices})

    except Exception as e:
        logger.error(f"Error fetching supplier prices: {e}")
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def end_of_day_detail(request, e_o_d_id):
    try:
        end_of_day = EndOfDay.objects.get(id=e_o_d_id)
        end_of_day_items = EndOfDayItems.objects.filter(end_of_day=end_of_day)
        
        total_amount_sold_today = Sale.objects.filter(date=localdate(), staff=False).aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0
        total_amount_staff_sold_today = Sale.objects.filter(date=localdate(), staff=True).aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0
        total_quantity_sold_today = SaleItem.objects.filter(sale__date=localdate(),).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0
        total_staff_portions = SaleItem.objects.filter(sale__date=localdate(), sale__staff=True).aggregate(total_staff_portions=Sum('quantity'))['total_staff_portions'] or 0
        difference =  end_of_day.cashed_amount - (total_amount_sold_today - total_amount_staff_sold_today) 
        
        taken_stock_value = Decimal(0)
        staff_portions_value = Decimal(0)
        portion_cost_value = Decimal(0)
        wastage_cost_value = Decimal(0)
        
        production_items = ProductionItems.objects.filter(production__date_created=end_of_day.date)
        
        ingredients = Ingredient.objects.select_related('raw_material').all()

        for item in production_items:
            
            logger.info(f'{item}:{item.wastage}')
            
            for ing in ingredients.filter(dish=item.dish):
                kgs_taken = Decimal(item.portions) / Decimal(item.dish.portion_multiplier)
                taken_stock_value += Decimal(ing.quantity) * kgs_taken * ing.raw_material.cost
        
                if item.staff_portions > 0:
                    kgs_staff = Decimal(item.staff_portions) / Decimal(item.dish.portion_multiplier)
                    staff_portions_value += Decimal(ing.quantity) * kgs_staff * ing.raw_material.cost   
        
        
        cogs_total = COGS.objects.filter(date=datetime.datetime.today()).aggregate(total_cogs=Sum('amount'))['total_cogs'] or 0
        gross_profit = total_amount_sold_today - cogs_total - wastage_cost_value
              
        for end in end_of_day_items:
            dish = Dish.objects.get(name=end.dish_name)
            portion_cost_value += Decimal(end.expected) * dish.price
            wastage_cost_value += Decimal(end.wastage) * dish.price
            
            logger.info(f'{wastage_cost_value} = {end.wastage} * {dish.price}')
            logger.info(f'{portion_cost_value} = {end.expected} * {ing.dish.price}')
        
        # total_staff_portions= end_of_day_items.objects.aggregate(total_staff_portions=Sum('staff_portions'))['total_staff_portions'] or 0
        
        buffer = generate_end_of_day_report(end_of_day, end_of_day_items, total_amount_staff_sold_today)
        send_end_of_day_report(request, buffer)
        
        logger.info('email sent')
    except Exception as e:
        logger.info(e)
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
            'difference': difference,
            'taken_stock_value':taken_stock_value,
            'staff_value':staff_portions_value,
            'portion_cost_value':portion_cost_value,
            'gross_profit':gross_profit,
            'wastage_cost_value':wastage_cost_value
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
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  
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


# @login_required # put to tasks
def send_end_of_day_report(request, buffer):
    logger.info(f'Sending Email')
    email = EmailMessage(
        f"End of Day Report:",
        "Please find the attached End of Day report. The expected amount is to be calculated on cost price, since they are no stipulated prices per dishes, but if they to be put the expected table will be relavant.",
        'admin@techcity.co.zw',
        ['cassymyo@gmail.com'],
    )
    email.attach(f'EndOfDayReport.pdf', buffer.getvalue(), 'application/pdf')
    
    EmailThread(email).start()

    logger.info(f' End of day report email sent.')
    

@login_required
def end_of_day_list(request):
    end_of_days = EndOfDay.objects.filter(done=True)
    logger.info(end_of_days)
    return render(request, 'end_of_day_list.html', {'eods':end_of_days})
 
@login_required 
def confirm_minor_raw(request):
    # payload 
    """
        {
            raw_material_id: float,
            quantity: float,
            production_id: int
        }
    """
    try:
        data = json.loads(request.body)
        
        raw_material_id = data.get('raw_material_id')
        quantity = data.get('quantity')
        production_id = data.get('production_id')
        quantity = float(quantity)
        
        with transaction.atomic():
            raw_material = Product.objects.select_for_update().get(id=raw_material_id)
            production = Production.objects.get(id=production_id)
            production_plan_item = ProductionItems.objects.filter(production=production, )
            
            p_raw_materials, created = ProductionRawMaterials.objects.get_or_create(
                product=raw_material,
                defaults={
                    "quantity": quantity,
                    "quantity_left": 0.0
                }  
            )
            
            AllocatedRawMaterials.objects.create(
                production=production,
                raw_material=raw_material,
                quantity=quantity
            )
            
            p_raw_materials.quantity += quantity
            p_raw_materials.save()
            
            raw_material.quantity -= quantity
            raw_material.save()
            
            Logs.objects.create(
                user=request.user, 
                action='Transfer',
                description='to production',
                product=raw_material,
                quantity=quantity,
                total_quantity=raw_material.quantity,
            )
            
            ProductionLogs.objects.create(
                user=request.user, 
                action='stock in',
                description='from warehouse',
                product=p_raw_materials,
                quantity=quantity,
                total_quantity=p_raw_materials.quantity,
            )

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'{e}'}, status=400)
    return JsonResponse({'success': True}, status=200)

@login_required
def calculate_reorder_point(product):
    average_weekly_usage = product.average_daily_usage * 7
    lead_time_in_weeks = product.lead_time / 7
    reorder_point = (average_weekly_usage * lead_time_in_weeks) + product.safety_stock
    return reorder_point


@login_required
def order_list(request):
    products = Product.objects.all()
    six_days_ago = timezone.now() - timedelta(days=6)
    lead_time = 1 # 1 days to be put to settings
    
    for product in products:
        if product.min_stock_level >= product.quantity:
            logger.info(product)
            quantity_last_six_days = Logs.objects.filter(timestamp__gte=six_days_ago, product=product).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 1
            
            reorder_quantity = quantity_last_six_days * lead_time + product.min_stock_level
            approx_days =  (product.quantity * 6) / reorder_quantity
            
            try:
                Reorder.objects.get_or_create(
                    product=product,
                    
                    defaults={
                        'ordered':False,
                        'approx_days':approx_days,
                        'reorder_quantity':reorder_quantity,
                    }
                )
            except Exception as e:
                logger.info(e)
                reorder_list = {}
            
    reorder_list = Reorder.objects.all()
    
    return render(request, 'inventory/reorder.html', {'reorders':reorder_list})


@login_required
def transfers(request):
    trans = Transfer.objects.all().order_by('-created_at')
    return render(request, 'inventory/transfers.html', {'transfers':trans})


@login_required
def production_transfers(request):
    trans = Transfer.objects.all().order_by('-created_at')
    
    return render(request, 'inventory/production_transfers.html', {'transfers':trans})


@login_required
def transfer_to_production(request):
    if request.method == 'GET':
        form = TransferForm()
        products = Product.objects.all()
        return render(request, 'inventory/add_transfer.html', {'form':form, 'products':products})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data.get('cart')
            
            with transaction.atomic():
                transfer = Transfer.objects.create(status=False)
                
                for item in items:
                    product_id = item['product_id']
                    quantity = float(item['quantity'])
                    logger.info(f'Processing quantity: {quantity}')
                    
                    product = Product.objects.get(id=product_id)
                    
                    TransferItems.objects.create(
                        transfer=transfer,
                        product=product,
                        quantity=quantity
                    )
                    
                    product.quantity -= quantity
                    product.save()
                    
                    logger.info(f'Updated product quantity: {product.quantity}')
                
                # send notification email
                transfer_notification(transfer.id)
                
            return JsonResponse({'success': True}, status=201)
        except Exception as e:
            transaction.rollback()
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)


@login_required
def accept_transfer(request, transfer_id):
    try:
        with transaction.atomic():

            transfer = Transfer.objects.get(id=transfer_id)
            transfer_items = TransferItems.objects.filter(transfer=transfer)

            for item in transfer_items:
                product, created = ProductionRawMaterials.objects.get_or_create(
                    product=item.product,
                    defaults={
                        'quantity': item.quantity
                    }
                )
                
                if not created:
                    product.quantity += item.quantity
                    product.save()

            transfer.status = True
            transfer.save()  

            messages.success(request, f'{transfer.transfer_number} successfully received')
            return redirect('inventory:production_transfers')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('inventory:receive_transfer_detail', transfer_id)
 
        
@login_required
def receive_transfers_detail(request, transfer_id):
    try:
        transfer = Transfer.objects.get(id=transfer_id)
        transfer_items = TransferItems.objects.filter(transfer=transfer)
        logger.info('one')
        return render(request, 'inventory/receive_transfer_detail.html', 
            {
                'transfer':transfer,
                'transfer_items':transfer_items
            }
        )
    except Exception as e:
        messages.warning(request, f'{e}')
        return redirect('inventory:production_transfers')
 
    
@login_required
def production_sales(request):
    filter_option = request.GET.get('filter', 'today')
    now = datetime.datetime.now()
    end_date = now
    
    if filter_option == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'this_week':
        start_date = now - timedelta(days=now.weekday())
    elif filter_option == 'yesterday':
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'this_month':
        start_date = now.replace(day=1)
    elif filter_option == 'last_month':
        start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    elif filter_option == 'this_year':
        start_date = now.replace(month=1, day=1)
    elif filter_option == 'custom':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    else:
        start_date = now - timedelta(days=now.weekday())
        end_date = now

    if filter_option == 'custom':
        production_data = ProductionItems.objects.filter(
            production__date_created__range=[start_date, end_date]
        ).values(
            'dish__name'
        ).annotate(
            total_wastage = Sum('wastage'),
            total_cost = Sum('total_cost'),
            total_portions=Sum('portions'),
            total_sold=Sum('portions_sold'),
            total_left_overs = Sum('left_overs')
        ).order_by('dish__name')
    else:
        production_data = ProductionItems.objects.filter(
            production__date_created__gte=start_date
        ).values(
            'dish__name'
        ).annotate(
            total_wastage = Sum('wastage'),
            total_cost = Sum('total_cost'),
            total_portions=Sum('portions'),
            total_sold=Sum('portions_sold'),
            total_left_overs = Sum('left_overs')
        ).order_by('dish__name')
        

    if request.GET.get('download') == 'csv':
        # Generate CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="production_sales_{filter_option}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Dish Name', 'Total Portions', 'Total Sold Portions'])

        for item in production_data:
            writer.writerow([item['dish__name'], item['total_portions'], item['total_sold']])

        return response

    return render(request, 'inventory/production_sales.html', {'production_data': production_data, 'filter_by': filter_option})

@login_required
def check_check_list(request):
    # Payload 
    """
    {
        "check_list_id": id
    }
    """
    try:
        data = json.loads(request.body)
        check_list_id = data.get('check_list_id')
        
        if not check_list_id:
            return JsonResponse({'success': False, 'message': 'Missing check_list_id'}, status=400)
        
        check_list_item = get_object_or_404(CheckList, id=check_list_id)
        
        check_list_item.status = not check_list_item.status
        
        check_list_item.save(update_fields=['status'])
        
        return JsonResponse({'success': True, 'message': 'Checklist status updated'}, status=200)
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
            
            