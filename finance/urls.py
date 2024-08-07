from django.urls import path
from . views import *

app_name = 'finance'

urlpatterns = [
    path('', finance, name='finance'),
    path('income_json/', income_json, name='income_json'),
    path('expense_json/', expense_json, name='expense_json'),
    path('income_graph/', income_graph, name='income_graph'),
    path('expense_graph/', expense_graph, name='expense_graph'),
    
    # expenses 
    path('expenses', expenses, name='expenses'),
    path('get_expense/<int:expense_id>/',get_expense, name='get_expense'),
    path('add/expense/', add_expense_category, name='add_expense_category'),
    path('edit/expense/', add_or_edit_expense, name='add_or_edit_expense'),
    path('delete_expense/<int:expense_id>/', delete_expense, name='delete_expense'),
    
    # cashbook 
    path('cashbook/', cashbook, name='cashbook')
]