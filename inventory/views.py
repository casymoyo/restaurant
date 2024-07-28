from . models import *
from . forms import (
    AddUOMForm,
    AddRawMaterialForm,
    AddProductCategoryForm,
    AddFinishedProductForm
)
from django.views import View    
from django.contrib import messages 
from django.http import JsonResponse
from django.shortcuts import render, redirect 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

# inventory logs function
def log(action, quantity, total_quantity, request, description):
    Logs.objects.create(
        user=request.user,
        quantity=quantity,
        total_quantity=total_quantity
        description = description
    )

class create_unit_of_measurement(LoginRequiredMixin, View):
    
    def get(self, request, *args, **kwargs):
        unit_of_measurements = UnitOfMeasurement.objects.all()
        return (list(unit_of_measurements), safe=False)
    
    def post(self, request, *args, **kwargs):
        # payload
        """
        name
        """
        if request.method == 'POST':
            form = AddUOMForm(request.POST)

            name = form.cleaned_data['name']
            
            if UnitOfMeasurement.objects.filter(name=name).exists():
                return JsonResponse(
                    {
                        'success':False,
                        'message':f'{name.upper()} exists!'
                    },
                    status = 400
                )
            
            if form.is_vald():
                form.save()
                return JsonResponse(
                    {
                        'success':True
                    },
                    status = 200
                )

class create_product_category(LoginRequiredMixin, View):
    
    def get(self, request, *args, **kwargs):
        product_categories = FinishedGoodsCategory.objects.all()
        return (list(product_categories), safe=False)
    
    def post(self, request, *args, **kwargs):
        # payload
        """
        name
        """
        if request.method == 'POST':
            form = AddProductCategoryForm(request.POST)

            name = form.cleaned_data['name']
            
            if AddProductCategoryForm.objects.filter(name=name).exists():
                return JsonResponse(
                    {
                        'success':False,
                        'message':f'{name.upper()} exists!'
                    },
                    status = 400
                )
            
            if form.is_vald():
                form.save()
                return JsonResponse(
                    {
                        'success':True
                    },
                    status = 200
                )
                
# raw materials views
class RawMaterials(LoginRequiredMixin, View):
    form = AddRawMaterialForm()
    u_o_m_form = AddUOMForm()
    template_name = 'inventory/raw_materials.html'
    
    def get(self, request, *args, **kwargs):
        raw_materials = RawMaterials.objects.all()
        
        return render(request, self.template_name, 
            {
                'form':self.form,
                'u_o_m_form':self.u_o_m_form,
                'raw_materials':raw_materials,
            }
        )
    
    def post(self, request, *args, **kwargs):
        # payload
        """
        name
        quantity
        unit: e.g kgs, litres, gramms , etc
        cost: per unit
        portion multiplier
        description: (optional)
        """
        
        if request.method == 'POST':
            form = AddRawMaterialForm(request.POST)
            
            name = form.cleaned_data['name']
            quantity = form.cleaned_dat['quantity']
            
            if form.is_valid():
                form.save()
                
                log('stock in', quantity, quantity, 'raw material stock in')
                
                return JsonResponse(
                    {
                        'success':True,
                        'message':f'{name.upper()}, successfully created'
                    },
                    status = 200
                )
            
            return JsonResponse(
                    {
                        'success':True,
                        'message':'invalid form data'
                    },
                    status = 400
                )

def edit_raw_material(request, raw_material_id):
    if request.method == 'POST':
        try:
            raw_material = RawMaterials.get(id=raw_material_id)
        except Exception as e:
            messages.warning(request, f'{e}')
            return redirect('inventory:inventory')
        
        form = AddRawMaterialForm(request.POST, instance=raw_material)
        
        name = form.cleaned_data['name']
        quantity = form.cleaned_dat['quantity']
        
        if form.is_valid():
            
            log('edit', quantity, quantity, f'stock edited from {raw_material.quantity} to {quantity}')
             
            form.save()
            
            messages.success(request, f'{name.upper()}, successfully edited')
            return render(request, 'inventory/raw_materials.html')
        
        messages.warning(request, 'Invalid form data')
        return render(request, 'inventory/edit_raw_materials.html')

def delete_raw_material(request, raw_material_id):
    try:
        raw_material = RawMaterials.get(id=raw_material_id)
    except Exception as e:
        messages.warning(request, f'{e}')
        return redirect('inventory:inventory')
    
    raw_material.deactivate = True
    return JsonResponse(
        {
            'success':True,
            'message':f'{raw_material.name.uper()}, successfully deleted'
        },
        status = 200
    )
    
                
# finished products views
class FinishedProducts(LoginRequiredMixin, View):
    form = AddFinishedProductForm()
    product_category_form = AddProductCategoryForm()
    template_name = 'inventory/products.html'
    
    def get(self, request, *args, **kwargs):
        products = FinishedProduct.objects.all()
        
        return render(request, self.template_name, 
            {
                'form':self.form,
                'u_o_m_form':self.u_o_m_form,
                'product_category_form':self.product_category_form,
                'products':products,
            }
        )
    
    def post(self, request, *args, **kwargs):
        # payload
        """
        name
        quantity
        cost: per unit
        category
        description: (also to be printed on the receipt)
        """
        
        if request.method == 'POST':
            form = AddRawMaterialForm(request.POST)
            
            name = form.cleaned_data['name']
            quantity = form.cleaned_dat['quantity']
            
            if form.is_valid():
                form.save()
                
                log('stock in', quantity, quantity, 'product stock in')
                
                return JsonResponse(
                    {
                        'success':True,
                        'message':f'{name.upper()}, successfully created'
                    },
                    status = 200
                )
            
            return JsonResponse(
                    {
                        'success':True,
                        'message':'invalid form data'
                    },
                    status = 400
                )

def edit_product(request, product_id):
    if request.method == 'POST':
        try:
            product = FinishedProduct.get(id=product_id)
        except Exception as e:
            messages.warning(request, f'{e}')
            return redirect('inventory:inventory')
        
        form = AddFinishedProductForm(request.POST, instance=product)
        
        name = form.cleaned_data['name']
        quantity = form.cleaned_dat['quantity']
        
        if form.is_valid():
            
            log('edit', quantity, quantity, f'stock edited from {product.quantity} to {quantity}')
             
            form.save()
            
            messages.success(request, f'{name.upper()}, successfully edited')
            return render(request, 'inventory/products.html')
        
        messages.warning(request, 'Invalid form data')
        return render(request, 'inventory/edit_product.html')

def delete_product(request, product_id):
    try:
        product = FinishedProduct.get(id=product_id)
    except Exception as e:
        messages.warning(request, f'{e}')
        return redirect('inventory:products')
    
    product.deactivate = True
    return JsonResponse(
        {
            'success':True,
            'message':f'{product.name.uper()}, successfully deleted'
        },
        status = 200
    )
    
# purchase order views

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
            contact = contact,
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
                return JsonResponse({'success': False, 'message':f'{supplier_id} does not exists'}, status=400)
                
        form = AddSupplierForm(request.post, instance=supplier)
        
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True}, status=400)
    return JsonResponse({'success': True})

@login_required
def purchase_orders(request):
    form = CreateOrderForm()
    orders = PurchaseOrder.objects.filter(branch = request.user.branch)
    return render(request, 'inventory/suppliers/purchase_orders.html', 
        {
            'form':form,
            'orders':orders
        }
    )
    

@login_required
def create_purchase_order(request):

    try:
        data = json.loads(request.body)
        purchase_order_data = data.get('purchase_order', {})
        purchase_order_items_data = data.get('items', [])
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON payload'}, status=400)

    supplier_id = purchase_order_data.get('supplier_id')
    delivery_date = purchase_order_data.get('delivery_date')
    status = purchase_order_data.get('status')
    notes = purchase_order_data.get('notes')

    if not all([supplier_id, delivery_date, status]):
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
                notes=notes
            )
            purchase_order.save()

            for item_data in purchase_order_items_data:
                product_id = item_data.get('product')
                quantity = item_data.get('quantity')
                unit_cost = item_data.get('unit_cost')

                if not all([product_id, quantity, unit_cost]):
                    transaction.set_rollback(True)
                    return JsonResponse({'success': False, 'message': 'Missing fields in item data'}, status=400)

                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    transaction.set_rollback(True)
                    return JsonResponse({'success': False, 'message': f'Product with ID {product_id} not found'}, status=404)

                PurchaseOrderItem.objects.create(
                    purchase_order=purchase_order,
                    product=product,
                    quantity=quantity,
                    unit_cost=unit_cost
                )

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': True, 'message': 'Purchase order created successfully'})

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
