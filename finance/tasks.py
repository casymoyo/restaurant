from finance.models import Expense
from utils.email import EmailThread
from django.core.mail import EmailMessage
from loguru import logger

def send_expense_creation_notification(expense_id):
    expense = Expense.objects.get(id=expense_id)
<<<<<<< HEAD
    
    email = EmailMessage(
        subject=f"Expense Notification:",
        body=f"""
        The email is to notify you on the creation of an expense for {expense.description}.
        For an amount of ${expense.amount}.
        """,
        from_email='admin@techcity.co.zw',
        to=['cassymyo@gmail.com'],
    )
    
=======
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
>>>>>>> d1c14cc97287c67047ba0ba1f6f8c7790636586a
    EmailThread(email).start()
    
    logger.info('send')
