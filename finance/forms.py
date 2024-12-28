from django import forms
from . models import *

class ExpensesForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['category', 'amount', 'description']
        
class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name']

class CashUpForm(forms.ModelForm):
    class Meta:
        model = CashUp
        fields = ['cashier', 'cashed_amount']
        
class ChangeForm(forms.ModelForm):
    class Meta:
        model : Change
        exclude = ['cacshier', 'collected', 'claimed']

class CashierExpenseForm(forms.ModelForm):
    class Meta:
        model = CashierExpense
        exclude = ['cashier', 'date']