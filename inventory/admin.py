from django.contrib import admin
from inventory.models import *

admin.site.register(Product)
admin.site.register(Dish)
admin.site.register(Production)
admin.site.register(ProductionItems)
admin.site.register(Meal)
admin.site.register(Ingredient)
admin.site.register(PurchaseOrder)