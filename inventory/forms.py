from . models import (
    Product, 
    Supplier,
    PurchaseOrder, 
    UnitOfMeasurement
)
from django import forms

class AddProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ['deactivate']

class AddSupplierForm(forms.ModelForm):   
    class Meta :
        model = Supplier
        fields = '__all__'

class CreateOrderForm(forms.ModelForm):
    class Meta:
        model =  PurchaseOrder
        exclude = ['order_number', 'branch']
        
class noteStatusForm(forms.ModelForm):
    class Meta:
        model =  PurchaseOrder
        fields = ['status', 'delivery_date', 'notes']
        
        widgets = {
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
class PurchaseOrderStatus(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['status']
        
class UnitOfMeasurementForm(forms.ModelForm):
    class Meta:
        model = UnitOfMeasurement
        fields = '__all__'
        
class EditProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ['quantity']
