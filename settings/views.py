from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import NotificationEmails
from .forms import NotificationEmailForm

def settings(request):
    return render(request, 'settings/settings.html')

def list_emails(request):
    emails = NotificationEmails.objects.all()
    return render(request, 'settings/notifications/list.html', {'emails': emails})

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
