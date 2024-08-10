from django.contrib.auth import get_user_model
from django.shortcuts import redirect


class CheckUsersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            User = get_user_model()
            if not User.objects.exists() and request.path != '/company/register-company/':
                return redirect('company:register-company')
        return self.get_response(request)
