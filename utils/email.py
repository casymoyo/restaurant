from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import threading
from django.core.mail import send_mail

import logging
logger = logging.getLogger(__name__)

def generate_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    response = HttpResponse(content_type="application/pdf")

    pdf_status = pisa.CreatePDF(html, dest=response)
    if pdf_status.err:
        return HttpResponse("Some errors were encountered <pre>" + html + "</pre>")

    return response

def send_mail_func(subject, message, html_content, from_email, to_email):
    
    def send_email_thread(subject, html_content, from_email, to_email):
        try:
            send_mail(
                subject,
                message,
                from_email,
                to_email,
                html_message=html_content,  
                fail_silently=False,
            )
            logger.info(f"[Email] -> Email sent successfully to {to_email} from {from_email}")
        except Exception as e:
            logger.info(f"[Email] -> Failed to send email: {e}")

    email_thread = threading.Thread(
        target=send_email_thread,
        args=(subject, html_content, from_email, to_email),
    )
    email_thread.start()





