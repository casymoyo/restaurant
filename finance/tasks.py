from finance.models import Expense
from utils.email import EmailThread
from django.core.mail import EmailMessage
from loguru import logger

def send_expense_creation_notification(expense_id):
    expense = Expense.objects.get(id=expense_id)
    
    email = EmailMessage(
        subject=f"Expense Notification:",
        body=f"""
        The email is to notify you on the creation of an expense for {expense.description}.
        For an amount of ${expense.amount}.
        """,
        from_email='admin@techcity.co.zw',
        to=['mirackletec@gmail.com'],
    )
    
    EmailThread(email).start()
    
    logger.info('send')
