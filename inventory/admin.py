from django.contrib import admin
from inventory.models import *

admin.site.register(Product)
admin.site.register(Dish)
admin.site.register(Production)
admin.site.register(ProductionItems)
admin.site.register(Meal)
admin.site.register(Ingredient)
admin.site.register(PurchaseOrder)
admin.site.register(EndOfDay)
admin.site.register(EndOfDayItems)
admin.site.register(MinorRawMaterials)
admin.site.register(ProductionRawMaterials)
admin.site.register(AllocatedRawMaterials)
admin.site.register(Transfer)
admin.site.register(Notification)
admin.site.register(CheckList)
admin.site.register(ProductionLogs)
