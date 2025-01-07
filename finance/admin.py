from django.contrib import admin
from . models import *

admin.site.register(SaleItem)
admin.site.register(Sale)
admin.site.register(Expense)
admin.site.register(ExpenseCategory)
admin.site.register(CashBook)
admin.site.register(COGS)
admin.site.register(CashUp)
admin.site.register(CashierAccount)
admin.site.register(transactionLog)
admin.site.register(CashierExpense)
