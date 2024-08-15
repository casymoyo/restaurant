from . models import (
    Dish, 
    Product, 
    Meal,
    Supplier,
    Production,
    Ingredient,
    PurchaseOrder, 
    MealCategory,
    UnitOfMeasurement,
    ProductionItems
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

# class productionForm(forms.ModelForm):
#     class Meta:
#         model = Production
#         fields = ['date_created', 'time_created']
        
class ProductionPlanInlineForm(forms.ModelForm):
    class Meta:
        model = ProductionItems
        fields = [
            'raw_material', 
            'dish', 
            'quantity', 
            'rm_carried_forward_quantity', 
            'lf_carried_forward_quantity', 
            'actual_quantity',
            'production_completion_time'
        ]
        widgets = {
            'raw_material': forms.Select(attrs={'class': 'form-control'}),
            'dish': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'rm_carried_forward_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'lf_carried_forward_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'actual_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'production_completion_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super(ProductionPlanInlineForm, self).__init__(*args, **kwargs)
        self.fields['raw_material'].queryset = Product.objects.filter(raw_material=True)

class DishForm(forms.ModelForm):
    class Meta:
        model = Dish
        fields = ['name', 'major_raw_material', 'portion_multiplier',]
             

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['minor_raw_material', 'quantity', 'note',]

class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ['name', 'price', 'category', 'dish']
        widgets = {
            'dish': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

class MealCategoryForm(forms.ModelForm):
    class Meta:
        model = MealCategory
        fields = '__all__'
