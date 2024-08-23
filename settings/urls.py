from django.urls import path
from . import views

app_name = 'settings'

urlpatterns = [
    path('', views.settings, name='settings'),
    path('emails', views.list_emails, name='list_emails'),
    path('create/', views.create_email, name='create_email'),
    path('update/<int:pk>/', views.update_email, name='update_email'),
    path('delete/<int:pk>/', views.delete_email, name='delete_email'),
]
