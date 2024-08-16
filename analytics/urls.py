from django.urls import path
from .views import *

urlpatterns = [
    path('analytics/', analytics_view, name='analytics_overview'),
    path('index/', analytics_index, name='analytics_index'),
]
