from celery import shared_task
from finance.models import Sale
from settings.models import Printer
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import cups

# @shared_task
# def print_receipt_task(sale_id):
#     # Your printing logic here
#     return f"Receipt printed successfully {sale_id}."

@shared_task
def print_receipt(context):
    # Render the PDF
    html = render_to_string('receipt_template.html', context)
    pdf = pisa.CreatePDF(html)

    # Save the PDF to a file
    with open('/tmp/receipt.pdf', 'wb') as f:
        f.write(pdf.dest.getvalue())

    # Connect to CUPS
    conn = cups.Connection()
    printers = conn.getPrinters()
    printer = Printer.objects.filter(is_default=True).first()  

    # Print the PDF
    conn.printFile(printer, '/tmp/receipt.pdf', 'Receipt', {})

    return "Printed successfully"