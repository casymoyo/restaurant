from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from loguru import logger
from utils.authenticate import authenticate_user
from .models import User
from .forms import UserRegistrationForm, UserDetailsForm, UserDetailsForm2
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password
from .models import Company, User
from .forms import CompanyForm, CustomUserCreationForm
from settings.models import Modules
from django.db import transaction

def create_company(request):
    if Company.objects.exists():
        return redirect('users:login')

    if request.method == 'POST':
        company_form = CompanyForm(request.POST)
        user_form = CustomUserCreationForm(request.POST)
        
        if company_form.is_valid() and user_form.is_valid():

            with transaction.atomic():
                # Save the company
                company = company_form.save()
                
                # Create the user with the company
                user = user_form.save(commit=False)
                user.company = company
                user.role = 'owner'  
                user.save()
                
                # create modules
                modules = ['Sales', 'Finance', 'Inventory', 'Production']
                bulk_modules = []

                for m in modules:
                    bulk_modules.append(Modules(name=m))

                Modules.objects.bulk_create(bulk_modules)
            return redirect('users:login')
        else:
            messages.warning(request, f'Company registration form not valid.')
    else:
        company_form = CompanyForm()
        user_form = CustomUserCreationForm()

    return render(request, 'create_company.html', {'company_form': company_form, 'user_form': user_form})


def users(request):
    search_query = request.GET.get('q', '')
    users = User.objects.filter(Q(username__icontains=search_query) | Q(email__icontains=search_query)).order_by(
        'first_name', 'last_name')
    form = UserRegistrationForm()
    user_details_form = UserDetailsForm2()

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            user = form.save(commit=False)
            user.password = make_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'User successfully added')
        else:
            messages.warning(request, 'Invalid form data')

    return render(request, 'auth/users.html', {'users': users, 'form': form, 'user_details_form': user_details_form})


def login_view(request):
    if request.method == 'POST':
        email_address = request.POST['email_address']
        password = request.POST['password']

        # Validate email
        try:
            validate_email(email_address)
        except ValidationError:
            messages.error(request, 'Invalid email format')
            return render(request, 'auth/login.html')

        user = authenticate_user(email=email_address, password=password)
        logger.info(f'User: {user}')
        if user is not None:
            if user.is_active:
                login(request, user)
                logger.info(f'User: {user.first_name + " " + user.email} logged in')
                logger.info(f'User role: {user.role}')

                # session_key = request.session.session_key
                # user.session_key = session_key
                # user.save()

                # logger.info(f'logged with session key: {session_key}')
                if user.role in ['accountant', 'admin', 'owner']:
                    logger.info(f'User: {user.first_name + " " + user.email} is an {user.role}')
                    return redirect('dashborad')
                elif user.role == 'chef':
                    return redirect('inventory:production_plans')
                return redirect('pos:pos')
            else:
                messages.error(request, 'Your account is not active, contact admin')
        else:
            messages.warning(request, 'Invalid username or password')

    return render(request, 'auth/login.html')


def user_edit(request, user_id):
    user = User.objects.get(id=user_id)
    logger.info(f'User details: {user.first_name + " " + user.email}')
    if request.method == 'POST':
        form = UserDetailsForm2(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'User details updated successfully')
            return redirect('users:user_detail', user_id=user.id)
        else:
            messages.error(request, 'Invalid form data')
    else:
        form = UserDetailsForm2(instance=user)
    return render(request, 'auth/users.html', {'user': user, 'form': form})


def user_detail(request, user_id):
    user = User.objects.get(id=user_id)
    form = UserDetailsForm()

    logger.info(f'User details: {user.first_name + " " + user.email}')
    # render user details
    if request.method == 'GET':
        return render(request, 'users/user_detail.html', {'user': user, 'form': form})
    if request.method == 'POST':
        form = UserDetailsForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'User details updated successfully')
        else:
            messages.error(request, 'Invalid form data')
        return render(request, 'users/user_detail.html', {'user': user, 'form': form})


def register(request):
    form = UserRegistrationForm()
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            user = form.save(commit=False)
            user.password = make_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'User successfully added')
        else:
            messages.error(request, 'Error')
    return render(request, 'auth/register.html', {
        'form': form
    })



def get_user_data(request, user_id):
    user = User.objects.get(id=user_id)
    user_data = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'username': user.username,
        'phonenumber': user.phonenumber,
        'role': user.role,
    }
    logger.info(f'User data: {user_data}')
    return JsonResponse(user_data)


def logout_view(request):
    logout(request)
    return redirect('users:login')
