from django.contrib import admin
from inventory.models import *

admin.site.register(Product)
admin.site.register(DeclaredLeftOverDish)
admin.site.register(DeclaredRawMaterial)
admin.site.register(Dish)
admin.site.register(Production)
admin.site.register(ProductionItems)