from django.contrib import admin
from . models import *

admin.site.register(SaleItem)
admin.site.register(Sale)
admin.site.register(Expense)
admin.site.register(ExpenseCategory)
admin.site.register(CashBook)