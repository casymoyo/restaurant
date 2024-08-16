from django.shortcuts import render, redirect
from .models import Printer
import cups

def settings(reques):
    pass

def list_printers(request):
    conn = cups.Connection()
    printers = conn.getPrinters()
    existing_printers = Printer.objects.all()
    return render(request, 'settings/printers/list.html', {'printers': printers, 'existing_printers': existing_printers})

def add_printer(request):
    if request.method == 'POST':
        printer_name = request.POST.get('printer_name')
        printer_location = request.POST.get('printer_location')
        is_default = request.POST.get('is_default', False)

        Printer.objects.create(name=printer_name, location=printer_location, is_default=is_default)
        return redirect('list_printers')
    return render(request, 'settings/printers/add_printer.html')

def set_default_printer(request, printer_id):
    Printer.objects.update(is_default=False)
    printer = Printer.objects.get(id=printer_id)
    printer.is_default = True
    printer.save()
    return redirect('list_printers')
