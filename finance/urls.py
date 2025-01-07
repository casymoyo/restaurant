from django.urls import path
from . views import *

app_name = 'finance'

urlpatterns = [
    path('', finance, name='finance'),
    path('pl_overview/', pl_overview, name='pl_overview'),
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
    path('update_expense_status/', update_expense_status, name='update_expense_status'),
    
    # cashbook 
    path('cashbook/', cashbook, name='cashbook'),
    path('cashbook/note/', cashbook_note, name='cashbook_note'),
    path('report/', download_cashbook_report, name='download_cashbook_report'),
    path('cancel-entry/', cancel_transaction, name='cancel-entry'),
    path('cashbook/note/<int:entry_id>/', cashbook_note_view, name='cashbook_note_view'),
    path('update_transaction_status/<int:pk>/', update_transaction_status, name='update_transaction_status'),
    
    # cogs
    path('cogs/', cogs_list, name='cogs'),
    
    # cashiers
    path('cashiers/', cashiers_list, name='cashiers_list'),
    
    # reports
    path('generate-report/', generate_report, name='generate_report'),
    
    # cash-ups
    path('cash_up/', cash_up, name='cash_up'),
    path('claim-cashup/<int:cashup_id>/', claim_cashup_difference, name='claim-cashup'),
    path('charge_cashup_difference/', charge_cashup_difference, name='charge_cashup_difference'),
    
    path('days_data', days_data, name='days_data'),

    #transaction logs
    path('transaction-logs', transaction_logs, name='logs'),

    #cashier expenses
    path('cashier-expenses/<int:cashier_id>/', cashier_expenses, name='cashier_expenses'),
]
