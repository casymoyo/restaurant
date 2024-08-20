from django import forms
from loguru import logger
from users.models import User, Company
from django.contrib.auth.forms import UserCreationForm
class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'username',
            'email',
            'phonenumber',
            'company',
            'role',
            'password'
        ]


class UserDetailsForm(forms.ModelForm):

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'username',
            'email',
            'phonenumber',
            'role',
        ]


class UserDetailsForm2(forms.ModelForm):
   
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'username',
            'email',
            'phonenumber',
            'role',
        ]

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'address']

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField(max_length=254)
    phonenumber = forms.CharField(max_length=13)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phonenumber', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user
