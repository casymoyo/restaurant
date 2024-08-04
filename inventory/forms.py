from . models import (
    Product, 
    Supplier,
    PurchaseOrder, 
    UnitOfMeasurement,
    ProductionPlanInline
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
        
class ProductionPlanInlineForm(forms.ModelForm):
    class Meta:
        model = ProductionPlanInline
        fields = ['product', 'dish', 'quantity', 'rm_carried_forward_quantity', 'lf_carried_forward_quantity', 'actual_quantity']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'dish': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'rm_carried_forward_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'lf_carried_forward_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'actual_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(ProductionPlanInlineForm, self).__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(raw_material=True)
