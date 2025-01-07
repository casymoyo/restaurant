from django.urls import path
from . import views

app_name = 'settings'

urlpatterns = [
    path('', views.settings, name='settings'),
    path('emails', views.list_emails, name='list_emails'),
    path('create/', views.create_email, name='create_email'),
    path('update/<int:pk>/', views.update_email, name='update_email'),
    path('delete/<int:pk>/', views.delete_email, name='delete_email'),
    path('add_notification/', views.add_email_notification, name='add_email_notification'),
    path('remove-email/<int:email_id>/', views.remove_email_notification, name='remove_email_notification')
]
