from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import NotificationEmails, Modules
from .forms import NotificationEmailForm
from users.models import User
from django.contrib import messages
from loguru import logger
from django.contrib.auth.decorators import login_required


@login_required
def settings(request):
    return render(request, 'settings/settings.html')

@login_required
def list_emails(request):
    emails = NotificationEmails.objects.all()
    modules = Modules.objects.all()
    users = User.objects.all()

    logger.info(emails)
    logger.info(modules)
    return render(request, 'settings/notifications/list.html', 
        {
            'notifications': emails,
            'modules':modules,
            'system_users':users
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