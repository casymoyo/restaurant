from django.http import HttpResponseForbidden

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.role == 'admin':
            return view_func(request, *args, **kwargs)
        else: return HttpResponseForbidden()
    return wrapper

def sales_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.role in ['sales', 'accountant', 'admin', 'Admin', 'owner', 'Owner']:
            return view_func(request, *args, **kwargs)
        else: return HttpResponseForbidden()
    return wrapper