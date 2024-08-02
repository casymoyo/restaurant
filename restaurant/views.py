from django.shortcuts import render

def Dashboard(request):
    return render(request, 'dashboard.html')