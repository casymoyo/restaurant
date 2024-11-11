import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import *
from .forms import NotificationEmailForm
from users.models import User
from django.contrib import messages
from loguru import logger
from django.contrib.auth.decorators import login_required
from inventory.models import Product


@login_required
def settings(request):
    return render(request, 'settings/settings.html')

@login_required
def list_emails(request):
    emails = NotificationEmails.objects.all()
    modules = Modules.objects.all()
    users = User.objects.all()

    permissions = Permission.objects.all()
    return render(request, 'settings/notifications/list.html', 
        {
            'notifications': emails,
            'modules':modules,
            'system_users':users,
            'permissions':permissions
        }
    )

def create_email(request):
    if request.method == 'POST':
        form = NotificationEmailForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success'})
    else:
        form = NotificationEmailForm()
    return render(request, 'settings/notifications/create.html', {'form': form})

def update_email(request, pk):
    email = get_object_or_404(NotificationEmails, pk=pk)
    if request.method == 'POST':
        form = NotificationEmailForm(request.POST, instance=email)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success'})
    else:
        form = NotificationEmailForm(instance=email)
    return render(request, 'settings/notifications/update.html', {'form': form, 'email': email})

def delete_email(request, pk):
    email = get_object_or_404(NotificationEmails, pk=pk)
    if request.method == 'POST':
        email.delete()
        return JsonResponse({'status': 'success'})
    return render(request, 'settings/notifications/delete.html', {'email': email})

@login_required
def add_email_notification(request):
    if request.method == 'POST':
        module_id = request.POST.get('module_id')
        email = request.POST.get('email')
        user_id = request.POST.get('user')

        # validation 
        if not module_id or not email and not user_id:
            messages.warning(request, 'Please select a user or Either fill in the email field.')
            return redirect('settings:list_emails')

        module = get_object_or_404(Modules, id=module_id)

        if user_id:
            user = get_object_or_404(User, id=user_id)
            email = user.email
        
        if NotificationEmails.objects.filter(module=module, email=email).exists():
            messages.warning(request, f'Email: {email} for module: {module.name} exists.')
            return redirect('settings:list_emails')

        NotificationEmails.objects.create(module=module, email=email)

        messages.success(request, f'Email: {email} for module: {module.name} successfully added.')

        return redirect('settings:list_emails') 
    return redirect('settings:list_emails')

@login_required
def remove_email_notification(request, email_id):
    try:
        logger.info(email_id)
        email = NotificationEmails.objects.get(id=email_id)
        email.delete()
        return JsonResponse({'status': 'success'}, status=200)
    except NotificationEmails.DoesNotExist:
        return JsonResponse({'error': 'Email not found'}, status=404)
    
@login_required
def stock_evaluation(request):
    if request.method == 'GET':
        products = Product.objects.all()
        methods = StockEvaluation.objects.all()
        return render(request, 'settings/stock_evaluation/stock_evaluation.html', {
            'products': products,
            'methods': methods
        })

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            method_id = data.get('method_id')

            product = Product.objects.get(id=product_id)

            if method_id:
                method = StockEvaluation.objects.get(id=method_id)
                product.stock_evaluation_method = method
                product.save()
                return JsonResponse({
                    'success': True,
                    'message': f'Stock evaluation method: {method.name} for product: {product.name} successfully saved.'
                }, status=201)
            else:
                # If method_id is empty, unassign the stock evaluation method
                product.stock_evaluation_method = None
                product.save()
                return JsonResponse({'success': True}, status=200)

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
def update_permission(request):
    user_id = request.POST.get('user_id')
    parent = request.POST.get('parent')
    name = request.POST.get('name')
    is_allowed = request.POST.get('is_allowed') == 'true' 

    user = User.objects.get(id=user_id)
    permission, created = Permission.objects.update_or_create(
        user=user,
        parent=parent,
        name=name,
        defaults={'is_allowed': is_allowed}
    )

    return JsonResponse({'success': True, 'created': created, 'is_allowed': permission.is_allowed})