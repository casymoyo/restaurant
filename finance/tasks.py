from finance.models import Expense
from utils.email import EmailThread
from django.core.mail import EmailMessage
from loguru import logger

def send_expense_creation_notification(expense_id):
    expense = Expense.objects.get(id=expense_id)
    logger.info(expense)
    email = EmailMessage(
        f"Expense Notification:",
        f"""
        The email is to notify you, on the creation of an expense for {expense.description}
        """
        'admin@techcity.co.zw',
        ['cassymyo@gmail.com']
    )
    # email.attach(f'EndOfDayReport.pdf', buffer.getvalue(), 'application/pdf')
    
    # Run email sending in a thread
    EmailThread(email).start()
    
    logger.info('send')
