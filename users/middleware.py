from django.shortcuts import redirect
from django.urls import reverse
from .models import Company

class CompanySetupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not Company.objects.exists():
            create_company_url = reverse('users:create_company')
            if request.path != create_company_url and not request.path.startswith('/static/'):
                return redirect(create_company_url)
        
        response = self.get_response(request)
        return response
