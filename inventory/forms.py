from . models import (
    RawMaterials,
    UnitOfMeasurement,
    FinishedGoodsCategory
)
from django.forms import forms

class AddRawMaterialForm(forms.Model):
    class Meta:
        model = RawMaterials
        fields = '__all__'
        
class AddUOMForm(forms.Model):
    class Meta:
        model = UnitOfMeasurement
        fields = '__all__'

class AddProductCategoryForm(forms.Model):
    class Meta:
        model = FinishedGoodsCategory
        fields = '__all__'

class AddFinishedProductForm(forms.Model):
    class Meta:
        model = RawMaterials
        fields = '__all__'

