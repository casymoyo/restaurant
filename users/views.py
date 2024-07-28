from django.db.models import Q
from django.views import View
from django.shortcuts import render,redirect
from .models import User
from .forms import UserRegistrationForm
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.hashers import make_password


def users(request):
    search_query = request.GET.get('q', '')
    users = User.objects.filter(Q(username__icontains=search_query) | Q(email__icontains=search_query))
    form = UserRegistrationForm()
    
    if request.method =='POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            user=form.save(commit=False)
            user.password=make_password(form.cleaned_data['password'])
            user.save() 
            messages.success(request, 'User successfully added')
        else: 
            messages.error(request, 'Invalid form data')
            
    return render(request, 'auth/users.html', {'users':users, 'form':form})
    

def login_view(request):
    if request.method =='POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(
            request,
            username=username,
            password=password
        )
        if user is not None:
            login(request, user)
            return redirect('pos:pos')
        else: messages.error(request, 'Invalid username or password')
    return render(request, 'auth/login.html')

def user_edit(request, user_id):
    user = User.objects.get(id=user_id)
    pass

def user_detail(request, user_id):
    user = User.objects.get(id=user_id)
    pass


def register(request):
    form = UserRegistrationForm()
    if request.method =='POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            user=form.save(commit=False)
            user.password=make_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'User successfully added')
        else: 
            messages.error(request, 'Error')
    return render(request, 'auth/register.html', {
        'form':form
    })

def logout_view(request):
    logout(request)
    return redirect('users:login')
