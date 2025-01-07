from django import forms
from .models import NotificationEmails

class NotificationEmailForm(forms.ModelForm):
    class Meta:
        model = NotificationEmails
        fields = ['module', 'email']
