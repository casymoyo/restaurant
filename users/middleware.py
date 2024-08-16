from django.shortcuts import redirect
from users.models import Company

class CompanySetupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not Company.objects.exists() and request.path != '/create-company/':
            return redirect('create_company')
        response = self.get_response(request)
        return response
