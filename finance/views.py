import csv
from . models import *
import datetime, json
from loguru import logger
from . forms import (
    CashUpForm,
    ExpensesForm,
    ExpenseCategoryForm
)
from xhtml2pdf import pisa
from decimal import Decimal
from datetime import  timedelta
from django.db.models import Sum
from django.db import transaction
from .models import Sale, Expense, CashierPayments
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from . tasks import send_expense_creation_notification
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from inventory.models import Logs

def get_previous_month():
    first_day_of_current_month = datetime.datetime.now().replace(day=1)
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    return last_day_of_previous_month.month

def get_current_month():
    return datetime.datetime.now().month

def get_current_year():
    return datetime.datetime.now().year


# @login_required
def sale(request):
    sales = Sale.objects.all()
    return render(request, 'finance/sales.html', 
        {
            'sales':sales
        }    
    )
 
 
# @login_required   
def finance(request):
    sales = Sale.objects.filter(date__month = get_current_month(), void=False).order_by('-date')[:8]
    expenses = Expense.objects.filter(date__month = get_current_month()).order_by('-date')[:8]
    current_month = get_current_month()

    sales = Sale.objects.filter(date__month = current_month, staff=False, void=False)
    cogs = COGS.objects.filter(date__month = current_month)
    
    return render(request, 'finance/finance.html', 
        {
            'sales':sales,
            'expenses':expenses,
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
        filter_option = request.GET.get('filter', 'today')
        download = request.GET.get('download')
        
        now = datetime.datetime.now()
        end_date = now
        
        if filter_option == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_option == 'this_week':
            start_date = now - timedelta(days=now.weekday())
        elif filter_option == 'yesterday':
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_option == 'this_month':
            start_date = now.replace(day=1)
        elif filter_option == 'last_month':
            start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        elif filter_option == 'this_year':
            start_date = now.replace(month=1, day=1)
        elif filter_option == 'custom':
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        else:
            start_date = now - - timedelta(days=now.weekday())
            end_date = now
            
        expenses = Expense.objects.filter(date__gte=start_date, date__lte=end_date).order_by('date')
        
        if download:
            logger.info('download')
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="expenses_report_{filter_option}.csv"'

            writer = csv.writer(response)
            writer.writerow(['Date', 'Description', 'Done By', 'Amount'])

            total_expense = 0  
            for expense in expenses:
                total_expense += expense.amount

                writer.writerow([
                    expense.date,
                    expense.description,
                    expense.user.first_name,
                    expense.amount,
                ])

            writer.writerow(['Total', '', '', total_expense])
            
            return response
        
        return render(request, 'finance/expenses.html', 
            {
                'form':form,
                'cat_form':cat_form,
                'expenses':expenses,
                'filter_option': filter_option,
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
                user = request.user,
                cancel = False,
                description = description,
                status = True
            )
            if data.get('debit') == 'True':
                cashier_expenses_update = CashierExpense.objects.get(id = data.get('expense'))
                cashier_expenses_update.status = True
                cashier_expenses_update.save()

                CashBook.objects.create(
                    amount = amount,
                    expense = expense,
                    credit = True,
                    description=f'Expense ({expense.description[:20]})'
                )
            else:
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


@login_required
def cashbook(request):
    filter_option = request.GET.get('filter', 'today')
    now = datetime.datetime.now()
    end_date = now
    
    if filter_option == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'this_week':
        start_date = now - timedelta(days=now.weekday())
    elif filter_option == 'yesterday':
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'this_month':
        start_date = now.replace(day=1)
    elif filter_option == 'last_month':
        start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    elif filter_option == 'this_year':
        start_date = now.replace(month=1, day=1)
    elif filter_option == 'custom':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    else:
        start_date = now - timedelta(days=now.weekday())
        end_date = now

    entries = CashBook.objects.filter(date__gte=start_date, date__lte=end_date).order_by('date')
    
    total_debit = entries.filter(debit=True).aggregate(Sum('amount'))['amount__sum'] or 0
    total_credit = entries.filter(credit=True).aggregate(Sum('amount'))['amount__sum'] or 0
    
    balance_bf = 0 
    
    previous_entries = CashBook.objects.filter(date__lt=start_date)
    previous_debit = previous_entries.filter(debit=True).aggregate(Sum('amount'))['amount__sum'] or 0
    previous_credit = previous_entries.filter(credit=True).aggregate(Sum('amount'))['amount__sum'] or 0
    balance_bf = previous_debit - previous_credit

    total_balance = balance_bf + (total_debit - total_credit)
    
    sales = SaleItem.objects.filter(sale__void=False)

    return render(request, 'finance/cashbook.html', {
        'filter_option': filter_option,
        'entries': entries,
        'balance_bf': balance_bf,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'total_balance': total_balance,
        'end_date':end_date,
        'start_date':start_date,
        'sales':sales
    })

@login_required
def cashbook_note(request):
    #payload
    """
        entry_id:id,
        note:str
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            entry_id = data.get('entry_id')
            note = data.get('note')
            
            entry = CashBook.objects.get(id=entry_id)
            entry.note = note
            
            entry.save()
        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}.'}, status=400)
        return JsonResponse({'success':False, 'message':'Note successfully saved.'}, status=201)
    return JsonResponse({'success':False, 'message':'Invalid request.'}, status=405)

@login_required
def cashbook_note_view(request, entry_id):
    entry = get_object_or_404(CashBook, id=entry_id)
    
    if request.method == 'GET':
        notes = entry.notes.all().order_by('timestamp')
        notes_data = [
            {'user': note.user.username, 'note': note.note, 'timestamp': note.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
            for note in notes
        ]
        return JsonResponse({'success': True, 'notes': notes_data})
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            note_text = data.get('note')
            CashBookNote.objects.create(entry=entry, user=request.user, note=note_text)
            return JsonResponse({'success': True, 'message': 'Note successfully added.'}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)
    
@login_required
def cancel_transaction(request):
    #payload
    """
        entry_id:id,
    """
    try:
        data = json.loads(request.body)
        entry_id = data.get('entry_id')
        
        logger.info(entry_id)
        
        entry = CashBook.objects.get(id=entry_id)
        
        logger.info(entry)
        entry.cancelled = True
        
        if entry.director:
            entry.director = False
        elif entry.manager:
            entry.manager = False
        elif entry.accountant:
            entry.accountant = False
            
        entry.save()
        
        return JsonResponse({'success': True}, status=201)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
@login_required
def download_cashbook_report(request):
    filter_option = request.GET.get('filter', 'this_week')
    now = datetime.datetime.now()
    end_date = now
    
    if filter_option == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'this_week':
        start_date = now - timedelta(days=now.weekday())
    elif filter_option == 'yesterday':
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'this_month':
        start_date = now.replace(day=1)
    elif filter_option == 'last_month':
        start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    elif filter_option == 'this_year':
        start_date = now.replace(month=1, day=1)
    elif filter_option == 'custom':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    else:
        start_date = now - timedelta(days=now.weekday())
        end_date = now

    entries = CashBook.objects.filter(date__gte=start_date, date__lte=end_date).order_by('date')

    # Create a CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="cashbook_report_{filter_option}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Description', 'Expenses', 'Income', 'Balance'])

    balance = 0  
    for entry in entries:
        if entry.debit:
            balance += entry.amount
        elif entry.credit:
            balance -= entry.amount

        writer.writerow([
            entry.date,
            entry.description,
            entry.amount if entry.debit else '',
            entry.amount if entry.credit else '',
            balance,
            entry.accountant,
            entry.manager,
            entry.director
        ])

    return response


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
        sales_total = Sale.objects.filter(date=today, void=False).aggregate(Sum('total_amount'))
    else:
        sales_total = Sale.objects.filter(date__month=month, void=False).aggregate(Sum('total_amount'))
    
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
    
    
    return JsonResponse({'expense_total': expense_total['amount__sum'] or 0})


def income_graph(request):
    current_year = get_current_year()
    monthly_sales = Sale.objects.filter(date__year=current_year, void=False).values('date__month').annotate(total=Sum('total_amount')).order_by('date__month')
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


# @login_required
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
        current_month_sales = Sale.objects.filter(date=date_filter, void=False).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
        current_month_expenses = Expense.objects.filter(date=date_filter, cancel=False).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
        cogs_total = COGS.objects.filter(date=date_filter).aggregate(total_cogs=Sum('amount'))['total_cogs'] or 0
    elif filter_option == 'last_week':
        current_month_sales = Sale.objects.filter(date__range=date_filter, void=False).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
        current_month_expenses = Expense.objects.filter(date__range=date_filter, cancel=False).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
        cogs_total = COGS.objects.filter(date__range=date_filter).aggregate(total_cogs=Sum('amount'))['total_cogs'] or 0
    else:
        current_month_sales = Sale.objects.filter(date__range=date_filter, void=False).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
        current_month_expenses = Expense.objects.filter(date__range=date_filter, cancel=False).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
        cogs_total = COGS.objects.filter(date__range=date_filter).aggregate(total_cogs=Sum('amount'))['total_cogs'] or 0

    previous_month_sales = Sale.objects.filter(date__year=current_year, date__month=previous_month, void=False).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
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
    
    # net_income_change = calculate_percentage_change(current_net_income, previous_net_income)
    # gross_profit_change = calculate_percentage_change(current_gross_profit, previous_gross_profit)
    # gross_profit_margin_change = calculate_percentage_change(current_gross_profit_margin, previous_gross_profit_margin)


    data = {
        'net_profit':current_net_profit,
        'cogs_total':cogs_total,
        'current_expenses':current_expenses,
        'current_net_profit': current_net_profit,
        'previous_net_profit':previous_net_profit,
        'current_net_income': current_net_income,
        'previous_net_income': previous_net_income,
        'current_gross_profit': current_gross_profit,
        'previous_gross_profit': previous_gross_profit,
        'current_gross_profit_margin': f'{current_gross_profit_margin:.2f}',
        'previous_gross_profit_margin': previous_gross_profit_margin,
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

    sales_total = Sale.objects.filter(date__range=(start_date, end_date), void=False).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
    expenses_total = Expense.objects.filter(date__range=(start_date, end_date), cancel=False).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
    cogs_total = COGS.objects.filter(date__range=(start_date, end_date)).aggregate(total_cogs=Sum('amount'))['total_cogs'] or 0
    net_profit = sales_total - expenses_total - cogs_total
    gross_profit = sales_total - cogs_total

    context = {
        # 'user':request.user,
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
 
@login_required
def cash_up(request):
    if request.method == 'GET':
        form = CashUpForm()
        
        filter_option = request.GET.get('filter', 'today')
        download = request.GET.get('download')
        
        now = datetime.datetime.now()
        end_date = now
        
        if filter_option == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_option == 'this_week':
            start_date = now - timedelta(days=now.weekday())
        elif filter_option == 'yesterday':
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_option == 'this_month':
            start_date = now.replace(day=1)
        elif filter_option == 'last_month':
            start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        elif filter_option == 'this_year':
            start_date = now.replace(month=1, day=1)
        elif filter_option == 'custom':
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        else:
            start_date = now - - timedelta(days=now.weekday())
            end_date = now
            
        cashups = CashUp.objects.filter(date__gte=start_date, date__lte=end_date).order_by('date')
        
        if download:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="cashups_report_{filter_option}.csv"'

            writer = csv.writer(response)
            writer.writerow(['Date', 'Cashier', 'Done By', 'Sales' 'Cashed Amount', 'status'])

            for cashup in cashups:
                writer.writerow([
                    cashup.date,
                    cashup.cashier.first_name,
                    cashup.user.first_name,
                    cashup.sales,
                    'Done' if cashup.status else 'Not done'
                ])
            
            return response
        return render(request, 'finance/cashups.html', 
            {
                'form':form, 
                'cashups':cashups, 
                'filter_option':filter_option
            }
        )
    
    if request.method == 'POST':
        # payload
        """
            {
              cashier:id,
              cashed_amount:float,  
            } 
        """
        
        try:
            data = json.loads(request.body)
            cashed_amount = float(data.get('cashed_amount'))
            cashier = int(data.get('cashier'))
            
            if cashed_amount < 0:
                return JsonResponse({'success':False, 'message':f'Cashed amount cannot be less than zero.'}, status=400)
            
            cash_up = CashUp.objects.get(cashier__id=cashier, cashed=False)
            cash_up.cashed_amount = Decimal(cashed_amount)

            cash_up.difference = cash_up.cashed_amount - (cash_up.sales - cash_up.void_amount - cash_up.expenses + cash_up.change)
            cash_up.cashed = True
            cash_up.save()

        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}'}, status=400)
        return JsonResponse({'success':True, 'message':f'Cash Up successfully created'}, status=201)
    return JsonResponse({'success':False, 'message':f'Invalid request'}, status=405)

@login_required
@transaction.atomic
def claim_cashup_difference(request, cashup_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cashup_id = data.get('cashup_id')
            claim_amount = data.get('claim_amount')

            cash_up = CashUp.objects.select_for_update().get(id=cashup_id)
            
            if cash_up.status:
                return JsonResponse({'success': False, 'message': f'Cash up already processed'}, status=400)
            
            cash_up.status = True
            cash_up.save()

            CashBook.objects.create(
                amount=claim_amount,
                debit=True,
                credit=False,
                description='Over cash up claim',
            )

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'{e}'}, status=400)
        return JsonResponse({'success': True, 'message': 'Cash Up successfully claimed'}, status=201)
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=405)

@login_required
@transaction.atomic
def charge_cashup_difference(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cashup_id = data.get('cashup_id')
            charge_amount = data.get('charge_amount')

            logger.info(charge_amount)
            cash_up = CashUp.objects.select_for_update().get(id=cashup_id)
            
            if cash_up.status:
                return JsonResponse({'success': False, 'message': f'Cash up already processed'}, status=400)
            
            cash_up.status = True
            cash_up.save()

            CashierAccount.objects.create(
                cashier = cash_up.cashier,
                cash_up = cash_up,
                amount=charge_amount,
                status = False
            )

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'{e}'}, status=400)
        return JsonResponse({'success': True, 'message': 'Cash Up successfully claimed'}, status=201)
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=405)

@login_required
def cashiers_list(request):
    
    if request.method == 'GET':
        cashiers = CashierAccount.objects.all()
        return render(request, 'finance/cashiers.html', {'cashiers':cashiers})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cashier_id = data.get('cashier_id')
            amount = Decimal(data.get('amount'))
            
            cashier = CashierAccount.objects.get(id=cashier_id)
            cashups = CashUp.objects.filter(cashier=cashier.cashier).order_by('-id')
            
            for cashup in cashups:
                outstanding_balance = cashup.sales - cashup.cashed_amount
                
                if amount >= outstanding_balance:
                    # If the amount is enough to cover this cashup entry, reduce the amount
                    amount -= outstanding_balance
                    cashup.cashed_amount += outstanding_balance
                    cashup.save()
                    
                    if amount == 0:
                        break
                else:
                    # If the amount is not enough to cover this entry completely, deplete it and stop
                    cashup.cashed_amount += amount
                    amount = 0
                    cashup.save()
                    break
            
            # Check if all cashups are fully paid
            all_paid = all((cu.sales == cu.cashed_amount) for cu in cashups)
            if all_paid:
                cashier.status = True
                cashier.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

@login_required
def update_transaction_status(request, pk):
    if request.method == 'POST':
        entry = get_object_or_404(CashBook, pk=pk)
        
        data = json.loads(request.body)
        
        status = data.get('status')
        field = data.get('field')  

        if field in ['manager', 'accountant', 'director']:
            setattr(entry, field, status)

            if entry.cancelled:
                entry.cancelled = False
            entry.save()
            return JsonResponse({'success': True, 'status': getattr(entry, field)})
        
    return JsonResponse({'success': False}, status=400)

@login_required
def update_expense_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            expense_id = data.get('id')
            status = data.get('status')

            expense = Expense.objects.get(id=expense_id)
            expense.status = status
            expense.save()

            return JsonResponse({'success': True, 'message': 'Status updated successfully.'})
        except Expense.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Expense not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
def days_data(request):
    current_month = get_current_month()

    sales = Sale.objects.filter(date__month=current_month, staff=False, void=False)
    cogs = COGS.objects.filter(date__month=current_month)

    first_day = min(sales.first().date, cogs.first().date)
    
    def get_week_data(queryset, start_date, end_date, amount_field):
        week_data = queryset.filter(date__gte=start_date, date__lt=end_date).values(amount_field, 'date')
        total = week_data.aggregate(total=Sum(amount_field))['total'] or 0
        return week_data, total

    data = {}
    for week in range(1, 5):
        week_start = first_day + timedelta(days=(week-1)*7)
        week_end = week_start + timedelta(days=7)
        
        sales_data, sales_total = get_week_data(sales, week_start, week_end, 'total_amount')
        cogs_data, cogs_total = get_week_data(cogs, week_start, week_end, 'amount')
        
        data[f'week {week}'] = {
            'sales': list(sales_data),
            'cogs': list(cogs_data),
            'total_sales': sales_total,
            'total_cogs': cogs_total
        }
    
    return JsonResponse(data)

@login_required
def transaction_logs(request):
    transactions = Logs.objects.all()
    sale_items = SaleItem.objects.all()

    return render(request, 'transaction_logs.html', {
        'sale_items':sale_items,
        'transactions':transactions
    })

@login_required
def cashier_expenses(request, cashier_id):
    if request.method == 'GET':
        logger.info(request.user.role)
        if request.user.role in ['manager', 'superviser', 'admin', 'accountant']:
            expenses = CashierExpense.objects.all()
            expense_category = ExpenseCategory.objects.all()
        else:
            expenses = CashierExpense.objects.filter(cashier__id = cashier_id)

        total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
        logger.info(expenses)
        return render(request, 'finance/cashier_expenses.html', {
            'expenses':expenses,
            'categories': expense_category,
            'total_expenses':total_expenses
        })
    
    if request.method == 'POST':
        """
            name:str
            amount:float,
            description:str,
        """
        data = json.loads(request.body)
        name = data.get('name')
        amount = data.get('amount')
        description = data.get('description')
        
        if not name:
            return JsonResponse({'success':False, 'message':'Missing fields: name.'})
        
        if not amount:
            return JsonResponse({'success':False, 'message':'Missing fields: amount.'})
        
        CashierExpense.objects.create(
            name=name,
            amount=amount,
            description=description,
            cashier=request.user,
            status = False
        )
        
        return JsonResponse({'success':True, 'message':'Cashier expense successfully created.'}, status=201)
    
    if request.method == 'PUT':
        """
            expense_id:int
        """
        data = json.loads(request.body)
        logger.info(data)
        expense_id = data.get('expense_id')
        name = data.get('name')
        amount = float(data.get('amount'))
        description = data.get('description')

        logger.info(type(amount))
        try:
            expense = CashierExpense.objects.get(id=expense_id)
            
            expense.name = name
            expense.amount = amount
            expense.description = description
        
            expense.save()
            return JsonResponse({'success':True, 'message':'Cashier expense successfully updated.'}, status=201)
        except CashierExpense.DoesNotExist:
            return JsonResponse({'success':False, 'message':'Cashier expense not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}.'}, status=500)
        

    if request.method == 'DELETE':
        """
            expense_id:int
        """
        data = json.loads(request.body)
        expense_id = data.get('expense_id')
        
        try:
            expense = CashierExpense.objects.get(id=expense_id)
            expense.delete()
            return JsonResponse({'success':True, 'message':'Cashier expense successfully updated.'}, status=201)
        except CashierExpense.DoesNotExist:
            return JsonResponse({'success':False, 'message':'Cashier expense not found.'}, status=404)

    
    return JsonResponse({'success':False, 'message':'Invalid request method.'}, status=405)
