from utils.email import EmailThread
from . models import Production, Transfer
from django.core.mail import EmailMessage
from loguru import logger

def send_end_of_day_report(buffer):
    email = EmailMessage(
        f"End of Day Report:",
        "Please find the attached End of Day report. The expected amount is to be calculated on cost price, since they are no stipulated prices per dishes, but if they to be put the expected table will be relavant.",
        'admin@techcity.co.zw',
        ['cassymyo@gmail.com'],
    )
    email.attach(f'EndOfDayReport.pdf', buffer.getvalue(), 'application/pdf')
    
    EmailThread(email).start()

    logger.info(f' End of day report email sent.')
 

def send_production_creation_notification(production_id):
    production = Production.objects.get(id=production_id)
    
    email = EmailMessage(
        subject=f"Production Plan Creation",
        body=f"""
        The email is to notify you on the creation of a Production Plan {production.production_plan_number}, and it requires your cornifimation.
        """,
        from_email='admin@techcity.co.zw',
        to=['cassymyo@gmail.com'],
    )
    
    EmailThread(email).start()
    
    logger.info(f'Production confirmation ({production.production_plan_number}) sent.')
    

def transfer_notification(transfer_id):
    transfer = Transfer.objects.get(id=transfer_id)
    
    email = EmailMessage(
        subject="Raw Material Transfer Notification",
        body=f"""
        This is to notify you of a raw material transfer with the number {transfer.transfer_number}. 
        Please confirm receipt of this transfer.
        """,
        from_email='admin@techcity.co.zw',
        to=['cassymyo@gmail.com'],
    )
    
    EmailThread(email).start()
    
    logger.info(f'Notification for transfer {transfer.transfer_number} sent.')
    
    