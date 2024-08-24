from django.urls import path
from . views import *

app_name='users'

urlpatterns = [
    path('users/', users ,name='users'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register, name='register'),
    path('create-company/', create_company, name='create_company'),
    path('user/edit/<int:user_id>/', user_edit, name='user_edit'),
    path('user/detail/<int:user_id>/', user_detail, name='user_detail'),
    path('ajax/get-user-data/<int:user_id>/', get_user_data, name='ajax_get_user_data'),
]
