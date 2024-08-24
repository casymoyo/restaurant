from . models import *
import datetime, json
from loguru import logger
from . forms import (
    ExpensesForm,
    ExpenseCategoryForm
)
from xhtml2pdf import pisa
from decimal import Decimal
from datetime import  timedelta
from django.db.models import Sum
from django.db import transaction
from .models import Sale, Expense 
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from . tasks import send_expense_creation_notification
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required


def get_previous_month():
    first_day_of_current_month = datetime.datetime.now().replace(day=1)
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    return last_day_of_previous_month.month

def get_current_month():
    return datetime.datetime.now().month

def get_current_year():
    return datetime.datetime.now().year


@login_required
def sale(request):
    sales = Sale.objects.all()
    return render(request, 'finance/sales.html', 
        {
            'sales':sales
        }    
    )
 
 
@login_required   
def finance(request):
    sales = Sale.objects.filter(date__month = get_current_month()).order_by('-date')[:8]
    expenses = Expense.objects.filter(date__month = get_current_month()).order_by('-date')[:8]
    
    return render(request, 'finance/finance.html', 
        {
            'sales':sales,
            'expenses':expenses
        }
    )
 
 
@login_required   
def get_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    data = {
        'id': expense.id,
        'amount': expense.amount,
        'description': expense.description,
        'category': expense.category.id
    }
    return JsonResponse({'success': True, 'data': data})



@transaction.atomic #use with atomic
@login_required
def expenses(request):
    form = ExpensesForm()
    cat_form = ExpenseCategoryForm()
    if request.method == 'GET':
        expenses = Expense.objects.all().order_by('-date')
        return render(request, 'finance/expenses.html', 
            {
                'form':form,
                'cat_form':cat_form,
                'expenses':expenses
            }
        )
    
    if request.method == 'POST':
        #payload
        """
            {
                amount:float
                description:str
                category:id (int)
            }
        """
        try:
            data = json.loads(request.body)
            
            amount = data.get('amount')
            description = data.get('description')
            category = data.get('category')
            
            if not amount or not description or not category:
                return JsonResponse({'success':False, 'message':'Missing fields: amount, description, category.'})
            
            try:
                category = ExpenseCategory.objects.get(id=category)
            except ExpenseCategory.DoesNotExist:
                return JsonResponse({'success':False, 'message':f'Category with ID: {category}, doesn\'t exists.'})
            
            expense = Expense.objects.create(
                amount = amount,
                category = category,
                user = User.objects.get(id=1),
                cancel = False,
                description = description
            )
            
            CashBook.objects.create(
                amount = amount,
                expense = expense,
                credit = True,
                description=f'Expense ({expense.description[:20]})'
            )

            send_expense_creation_notification(expense.id)
            
            return JsonResponse({'success': True, 'messages':'Expense successfully created'}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required      
def add_or_edit_expense(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = data.get('amount')
            description = data.get('description')
            category_id = data.get('category')
            expense_id = data.get('id')

            if not amount or not description or not category_id:
                return JsonResponse({'success': False, 'message': 'Missing fields: amount, description, category.'})
            
            category = get_object_or_404(ExpenseCategory, id=category_id)

            if expense_id:  
                expense = get_object_or_404(Expense, id=expense_id)
                before_amount = expense.amount
                
                expense.amount = amount
                expense.description = description
                expense.category = category
                expense.save()
                message = 'Expense successfully updated'
                
                try:
                    cashbook_expense = CashBook.objects.get(expense=expense)
                    expense_amount = Decimal(expense.amount)
                    if cashbook_expense.amount < expense_amount:
                        cashbook_expense.amount = expense_amount
                        cashbook_expense.description = cashbook_expense.description + f'Expense (update from {before_amount} to {cashbook_expense.amount})'
                    else:
                        cashbook_expense.amount -= cashbook_expense.amount - expense_amount
                        cashbook_expense.description = cashbook_expense.description + f'(update from {before_amount} to {cashbook_expense.amount})'
                    cashbook_expense.save()
                except Exception as e:
                    return JsonResponse({'success': False, 'message': str(e)}, status=400)
            return JsonResponse({'success': True, 'message': message}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)


@login_required
@transaction.atomic
def delete_expense(request, expense_id):
    if request.method == 'DELETE':
        try:
            expense = get_object_or_404(Expense, id=expense_id)
            expense.cancel = True
            expense.save()
            
            CashBook.objects.create(
                amount=expense.amount,
                debit=True,
                credit=False,
                description=f'Expense ({expense.description}): cancelled'
            )
            return JsonResponse({'success': True, 'message': 'Expense successfully deleted'})
        except Exception as e:
             return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)



@login_required # tune the filters
def cashbook(request):
    filter_option = request.GET.get('filter', 'this_week')
    now = datetime.datetime.now()

    if filter_option == 'this_week':
        start_date = now - timedelta(days=now.weekday()) 
    elif filter_option == 'yesterday':
        start_date = now - timedelta(days=1)
    elif filter_option == 'this_month':
        start_date = now.replace(day=1)
    elif filter_option == 'last_month':
        start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    elif filter_option == 'this_year':
        start_date = now.replace(month=1, day=1)
    else:
        start_date = now - timedelta(days=now.weekday())

    entries = CashBook.objects.filter(date__gte=start_date).order_by('-date')
    
    debit_entries = entries.filter(debit=True)
    credit_entries = entries.filter(credit=True)

    return render(request, 'finance/cashbook.html', {
        'filter_option': filter_option,
        'debit_entries': debit_entries,
        'credit_entries': credit_entries,
    })


@login_required
def add_expense_category(request):
    categories = ExpenseCategory.objects.all().values()
    
    if request.method == 'POST':
        data = json.loads(request.body)
        category = data['name']
        logger.info(data)
        
        if ExpenseCategory.objects.filter(name=category).exists():
            return JsonResponse({'success':False, 'message':f'Category with ID {category} Exists.'}, status=400)
        
        ExpenseCategory.objects.create(
            name=category
        )
        return JsonResponse({'success':True}, status=201)
    return JsonResponse(list(categories), safe=False)


@login_required
def income_json(request):
    current_month = get_current_month()
    today = datetime.date.today()
    
    month = request.GET.get('month', current_month)
    day = request.GET.get('day', today.day)
    
    if request.GET.get('filter') == 'today':
        sales_total = Sale.objects.filter(date=today).aggregate(Sum('total_amount'))
    else:
        sales_total = Sale.objects.filter(date__month=month).aggregate(Sum('total_amount'))
    
    logger.info(f'Sales: {sales_total}')
    return JsonResponse({'sales_total': sales_total['total_amount__sum'] or 0})


@login_required
def expense_json(request):
    current_month = get_current_month()
    today = datetime.date.today()
    
    month = request.GET.get('month', current_month)
    day = request.GET.get('day', today.day)
    
    if request.GET.get('filter') == 'today':
        expense_total = Expense.objects.filter(date=today, cancel=False).aggregate(Sum('amount'))
    else:
        expense_total = Expense.objects.filter(date__month=month, cancel=False).aggregate(Sum('amount'))
    
    logger.info(f'Expenses: {expense_total}')
    return JsonResponse({'expense_total': expense_total['amount__sum'] or 0})


@login_required
def income_graph(request):
    current_year = get_current_year()
    monthly_sales = Sale.objects.filter(date__year=current_year).values('date__month').annotate(total=Sum('total_amount')).order_by('date__month')
    data = {month['date__month']: month['total'] for month in monthly_sales}
    return JsonResponse(data)


@login_required
def expense_graph(request):
    current_year = get_current_year()
    monthly_expenses = Expense.objects.filter(date__year=current_year).values('date__month').annotate(total=Sum('amount')).order_by('date__month')
    data = {month['date__month']: month['total'] for month in monthly_expenses}
    return JsonResponse(data)



@login_required
def calculate_percentage_change(current_value, previous_value):
    if previous_value == 0:
        return 0 if current_value == 0 else 100
    return ((current_value - previous_value) / previous_value) * 100


@login_required
def cogs_list(request):
    cogs = COGS.objects.all()
    return render(request, 'finance/cogs.html', {'cogs':cogs})


@login_required
def pl_overview(request):
    filter_option = request.GET.get('filter')
    today = datetime.date.today()
    previous_month = get_previous_month()
    current_year = today.year
    current_month = today.month

    if filter_option == 'today':
        date_filter = today
    elif filter_option == 'last_week':
        last_week_start = today - datetime.timedelta(days=today.weekday() + 7)
        last_week_end = last_week_start + datetime.timedelta(days=6)
        date_filter = (last_week_start, last_week_end)
    elif filter_option == 'this_month':
        date_filter = (datetime.date(current_year, current_month, 1), today)
    elif filter_option == 'year':
        year = int(request.GET.get('year', current_year))
        date_filter = (datetime.date(year, 1, 1), datetime.date(year, 12, 31))
    else:
        date_filter = (datetime.date(current_year, current_month, 1), today)

    if filter_option == 'today':
        current_month_sales = Sale.objects.filter(date=date_filter).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
        current_month_expenses = Expense.objects.filter(date=date_filter, cancel=False).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
        cogs_total = COGS.objects.filter(date=date_filter).aggregate(total_cogs=Sum('amount'))['total_cogs'] or 0
    elif filter_option == 'last_week':
        current_month_sales = Sale.objects.filter(date__range=date_filter).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
        current_month_expenses = Expense.objects.filter(date__range=date_filter, cancel=False).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
        cogs_total = COGS.objects.filter(date__range=date_filter).aggregate(total_cogs=Sum('amount'))['total_cogs'] or 0
    else:
        current_month_sales = Sale.objects.filter(date__range=date_filter).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
        current_month_expenses = Expense.objects.filter(date__range=date_filter, cancel=False).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
        cogs_total = COGS.objects.filter(date__range=date_filter).aggregate(total_cogs=Sum('amount'))['total_cogs'] or 0

    previous_month_sales = Sale.objects.filter(date__year=current_year, date__month=previous_month).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
    previous_month_expenses = Expense.objects.filter(date__year=current_year, date__month=previous_month, cancel=False).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
    previous_cogs =  COGS.objects.filter(date__year=current_year, date__month=previous_month).aggregate(total_cogs=Sum('amount'))['total_cogs'] or 0
    
    current_net_income = current_month_sales
    previous_net_income = previous_month_sales 
    current_expenses = current_month_expenses 
    
    current_gross_profit = current_month_sales - cogs_total
    previous_gross_profit = previous_month_sales - previous_cogs
    
    current_net_profit = current_gross_profit - current_month_expenses
    previous_net_profit = previous_gross_profit - previous_month_expenses

    current_gross_profit_margin = (current_gross_profit / current_month_sales * 100) if current_month_sales != 0 else 0
    previous_gross_profit_margin = (previous_gross_profit / previous_month_sales * 100) if previous_month_sales != 0 else 0
    
    net_income_change = calculate_percentage_change(current_net_income, previous_net_income)
    gross_profit_change = calculate_percentage_change(current_gross_profit, previous_gross_profit)
    gross_profit_margin_change = calculate_percentage_change(current_gross_profit_margin, previous_gross_profit_margin)


    data = {
        'net_profit':current_net_profit,
        'cogs_total':cogs_total,
        'current_expenses':current_expenses,
        'current_net_profit': current_net_profit,
        'previous_net_profit':previous_net_profit,
        'current_net_income': current_net_income,
        'previous_net_income': previous_net_income,
        'net_income_change': net_income_change,
        'current_gross_profit': current_gross_profit,
        'previous_gross_profit': previous_gross_profit,
        'gross_profit_change': f'{gross_profit_change:.2f}',
        'current_gross_profit_margin': f'{current_gross_profit_margin:.2f}',
        'previous_gross_profit_margin': previous_gross_profit_margin,
        'gross_profit_margin_change': gross_profit_margin_change,
    }
    
    return JsonResponse(data)


@login_required
def generate_report(request):
    time_frame = request.GET.get('timeFrame')
    start_date = None
    end_date = None

    if time_frame == 'today':
        start_date = end_date = datetime.datetime.today()
    elif time_frame == 'weekly':
        start_date = datetime.datetime.today()- timedelta(days=7)
        end_date = datetime.datetime.today()
    elif time_frame == 'monthly':
        start_date = datetime.datetime.today() - timedelta(days=30)
        end_date = datetime.datetime.today()
    elif time_frame == 'yearly':
        start_date = datetime.datetime.today() - timedelta(days=365)
        end_date = datetime.datetime.today()
    elif time_frame == 'custom':
        start_date = datetime.datetime.strptime(request.GET.get('startDate'), '%Y-%m-%d')
        end_date = datetime.datetime.strptime(request.GET.get('endDate'), '%Y-%m-%d')

    sales_total = Sale.objects.filter(date__range=(start_date, end_date)).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
    expenses_total = Expense.objects.filter(date__range=(start_date, end_date), cancel=False).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
    cogs_total = COGS.objects.filter(date__range=(start_date, end_date)).aggregate(total_cogs=Sum('amount'))['total_cogs'] or 0
    net_profit = sales_total - expenses_total - cogs_total
    gross_profit = sales_total - cogs_total

    context = {
        'user':request.user,
        'sales_total': sales_total,
        'expenses_total': expenses_total,
        'cogs_total': cogs_total,
        'net_profit': net_profit,
        'time_frame': time_frame,
        'start_date': start_date,
        'end_date': end_date,
        'gross_profit': gross_profit
    }

    html_string = render_to_string('finance/income_statement_template.html', context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="income_statement_{time_frame}.pdf"'
    pisa_status = pisa.CreatePDF(html_string, dest=response)

    if pisa_status.err:
        logger.info('We had some errors with generating the report')
        return HttpResponse('We had some errors with generating the report')
    
    return response
 