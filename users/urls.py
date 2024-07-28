from django.urls import path
from . views import *

app_name='users'

urlpatterns = [
    path('users/', users ,name='users'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register, name='register'),
    path('user/edit/<int:user_id>/', user_edit, name='user_edit'),
    path('user/detail/<int:user_id>/', user_detail, name='user_detail' )
]
