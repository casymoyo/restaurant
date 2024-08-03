import json
from . models import *
from loguru import logger
from decimal import Decimal
from django.views import View    
from django.contrib import messages 
from django.http import JsonResponse
from django.shortcuts import render, redirect 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from loguru import logger
from django.contrib.auth import get_user_model

from . forms import (
    AddProductForm,
    AddSupplierForm,
    CreateOrderForm,
    noteStatusForm,
    PurchaseOrderStatus,
    UnitOfMeasurementForm,
    EditProductForm,
    ProductionPlanInlineForm
)


# to be removed
user = get_user_model()

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
            return JsonResponse({'success':False, 'message':f'Category Doesnt Exists'})
        
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
            portion_multiplier = data['portion_multiplier']
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

def product_detail(request, product_id):
    try: 
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        messages.warning(request, f'Product with ID: {product_id} doesnt exists')
        
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
        messages.warning(request, f'Product with ID: {product_id} doesnt exists')
        
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
                return JsonResponse({'success': False, 'message':f'{supplier_id} does not exists'}, status=400)
                
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

                    # update finance accounts vat input account and the PurchasesAccount
                    # if purchase_order.status == 'received':
                    #     # change currency (first initial to be default ??)
                    #     try:
                    #         currency = Currency.objects.get(default=True)
                            
                    #         PurchaseOrderAccount.objects.create(
                    #             purchase_order = purchase_order,
                    #             amount = purchase_order.total_cost - purchase_order.tax_amount,
                    #             balance = 0,
                    #             expensed = False
                    #         )
                            
                    #     except Currency.DoesNotExist:
                    #         return JsonResponse({'success':False, 'message':f'currency doesnt exists'})
                        
                    #     try:
                    #         rate = VATRate.objects.get(status=True)
                    #         logger.info(f'rate -> {rate}')
                    #         VATTransaction.objects.create(
                    #             purchase_order = purchase_order,
                    #             vat_type='Input',
                    #             vat_rate = rate.rate,
                    #             tax_amount = tax_amount
                    #         )
                            
                    #     except VATRate.DoesNotExist:
                    #         return JsonResponse({'success':False, 'message':f'Make sure you have a stipulated vat rate in the system'})
          
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

        return JsonResponse({'success': True, 'message': 'Purchase order created successfully'})
    
# @login_required
@transaction.atomic
def change_purchase_order_status(request, order_id):
    try:
        purchase_order = PurchaseOrder.objects.get(id=order_id)
    except PurchaseOrder.DoesNotExist:
        return JsonResponse({'error': f'Purchase order with ID: {order_id} does not exist'}, status=404)

    try:
        data = json.loads(request.body)
        status = data['status']
        
        if status:
            purchase_order.status=status
            if purchase_order.status == 'received':
            #     try:
            #         currency = Currency.objects.get(default=True)
                    
            #         PurchaseOrderAccount.objects.create(
            #             purchase_order = purchase_order,
            #             amount = purchase_order.total_cost - purchase_order.tax_amount,
            #             balance = 0,
            #             expensed = False
            #         )
                    
            #     except Currency.DoesNotExist:
            #         return JsonResponse({'success':False, 'message':f'currency doesnt exists'})
                
            #     try:
            #         rate = VATRate.objects.get(status=True)
                    
            #         VATTransaction.objects.create(
            #             purchase_order = purchase_order,
            #             vat_type='Input',
            #             vat_rate = rate.rate,
            #             tax_amount = purchase_order.tax_amount
            #         )
                    
            #     except VATRate.DoesNotExist:
            #         return JsonResponse({'success':False, 'message':f'Make sure you have a stipulated vat rate in the system'})
                purchase_order.save()
            
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
        messages.warning(request, f'Purchase order with ID: {order_id} does not exists')
        return redirect('inventory:purchase_orders')
    
    try:
        purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order)
    except PurchaseOrderItem.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} does not exists')
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
        messages.warning(request, f'Purchase order with ID: {order_id} does not exists')
        return redirect('inventory:purchase_orders')
    
    try:
        purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order)
    except PurchaseOrderItem.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} does not exists')
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
        messages.warning(request, f'Purchase order with ID: {order_id} does not exists')
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
            return JsonResponse({'success': False, 'message': f'Purchase Order Item with ID: {order_item_id} does not exist'}, status=404)

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
            return JsonResponse({'success': False, 'message': f'Product with ID: {order_item.product.id} does not exist'}, status=404)
            
        
        Logs.objects.create(
            purchase_order = purchase_order,
            user= user.objects.get(id=1),  #to be removed,
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
    plans = Production.objects.all()
    return render(request, 'inventory/production_plans.html', {'plans':plans})


def create_production_plan(request):
    
    if request.method == 'POST':
        # Payload
        """
        {
            "items": [
                {
                    "raw_material": id,
                    "quantity": int,
                    "dish": id
                }
            ]
        }
        """
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON data: {e}'}, status=400)
        
        items = data.get('items')
        
        if not items or not isinstance(items, list):
            return JsonResponse({'success': False, 'message': 'Invalid data: items should be a list'}, status=400)
        
        for item in items:
            raw_material_id = item.get('raw_material')
            quantity = item.get('quantity')
            dish_id = item.get('dish')
            
            if not raw_material_id or not quantity or not dish_id:
                return JsonResponse({'success': False, 'message': 'Missing data: raw material, quantity, or dish'}, status=400)
            
            try:
                raw_material = Product.objects.get(id=raw_material_id)
            except Product.DoesNotExist:
                return JsonResponse({'success': False, 'message': f'Raw Material with ID: {raw_material_id} does not exist'}, status=404)
                
            try:
                dish = Dish.objects.get(id=dish_id)
            except Dish.DoesNotExist:
                return JsonResponse({'success': False, 'message': f'Dish with ID: {dish_id} does not exist'}, status=404)
            
            # Create and save the production plan
            production_plan = Production(status=False)
            production_plan.save()
            
            ProductionItems.objects.create(
                production=production_plan,
                raw_material=raw_material,
                quantity=quantity,
                dish=dish
            )
        
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
    raw_material:id 
    
    """
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f'data->{data}')
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON data: {e}'}, status=400)
        
        raw_material_id = data.get('raw_material')
        
        if not raw_material_id:
            return JsonResponse({'success': False, 'message': 'Missing data: raw material'}, status=400)
        
        try:
            raw_material = Product.objects.get(id=raw_material_id)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Raw Material with ID: {raw_material_id} does not exist'}, status=404)
            
        # check yesterday if they are left raw materials
        
        yesterday = datetime.date.today() - datetime.timedelta(days=1)

        is_yesterday_sunday = yesterday.weekday() == 6 
        
        

        if is_yesterday_sunday:
            logger.info(f'Date: sunday few meals cooked no, balances')
            return JsonResponse(
                {
                    'success':True, 
                    'data':{
                        'raw_material_dif':0,
                        'left_over_portion_diff':0
                    }
                }
            )
        else:
            if DeclaredRawMaterial.objects.all().exists():
                logger.info('here')
                yesterday_raw_materiral = DeclaredRawMaterial.objects.get(raw_material=raw_material, date=yesterday)
                
                try:
                    yesterday_left_over = DeclaredLeftOverDish.objects.get(dish__raw_material=raw_material, date=yesterday)
                except DeclaredLeftOverDish.DoesNotExist:
                    return JsonResponse({'success':False, 'message':f'Left over dish with DATE: {yesterday}, doesnt exists'})
            
                try:
                    production = Production.objects.get(id=1)  #to be changed
                    production_plan_item = ProductionItems.objects.get(production=production, raw_material=raw_material)
                except Production.DoesNotExist:
                    return JsonResponse({'success':False, 'message':f'Production with DATE: {yesterday}, doesnt exists'})
                
                # calculate yesterday's quantity to be carried forward
        
                yesterday_raw_material_quantity_diff = production_plan_item.quantity - yesterday_raw_materiral.quantity
                
                logger.info(yesterday_raw_materiral)
                yesterday_left_over_portion_quantity = (yesterday_left_over.portion * \
                                                        (yesterday_raw_materiral.quantity * raw_material.portion_multiplier) ) \
                                                        / production_plan_item.quantity 
                logger.info(yesterday_left_over_portion_quantity)
                return JsonResponse(
                    {
                        'success':True, 
                        'data':{
                            'raw_material_dif':yesterday_raw_material_quantity_diff,
                            'left_over_portion_diff':yesterday_left_over_portion_quantity 
                        }
                    }
                )
            else:
                logger.info('hereee')
                return JsonResponse(
                    {
                        'success':True, 
                        'data':{
                            'raw_material_dif':0,
                            'left_over_portion_diff':0 
                        }
                    }
                )
        
        
        
