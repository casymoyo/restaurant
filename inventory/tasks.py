from utils.email import EmailThread
from . models import (
    Production, 
    ProductionItems,
    Transfer,
    Supplier,
    PurchaseOrderItem,
    PurchaseOrder,
    Product
)
from django.utils import timezone
from django.core.mail import EmailMessage
from utils.supplier_best_price import best_price
from loguru import logger
from settings.models import NotificationEmails
from utils.email_notification import modules_list
from celery import shared_task
from django.core.mail import send_mail
from users.models import User
from datetime import timedelta

def send_end_of_day_report(buffer):
    email = EmailMessage(
        f"End of Day Report:",
        "Please find the attached End of Day report. The expected amount is to be calculated on cost price, since they are no stipulated prices per dishes, but if they to be put the expected table will be relavant.",
        'admin@techcity.co.zw',
        ['mirackletec@gmail.com'],
    )
    email.attach(f'EndOfDayReport.pdf', buffer.getvalue(), 'application/pdf')
    
    EmailThread(email).start()

    logger.info(f' End of day report email sent.')

@shared_task
def send_production_creation_notification(production_id, items_list):
    production = Production.objects.get(id=production_id)

    m = f'Production plan {production.production_plan_number}'
    message = f"{m}\n\nProduction Items:\n{items_list}"

    recipient_list = [r['email'] for r in User.objects.all().values()]

    send_mail(
        'Production plan creation',
        message,
        'admin@techcity.co.zw',
        recipient_list,
        fail_silently=False,
    )

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
        to=['mirackletec@gmail.com'],
    )
    
    EmailThread(email).start()
    
    logger.info(f'Notification for transfer {transfer.transfer_number} sent.')

@shared_task
def supplier_email(supplier_id, purchase_order_item_id):
    purchase_order_item = PurchaseOrderItem.objects.get(id=purchase_order_item_id)
    supplier = Supplier.objects.get(id=supplier_id)

    purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order_item.purchase_order)

    price_list = [sup['price'] for sup in best_price(purchase_order_item.product.name)]
    min_price = min(price_list) if price_list else None

    def send_email(po_item):
        logger.info("Preparing to send email for: %s", po_item)

        recipient_list = [r['email'] for r in User.objects.all().values() if r['role'] in ['admin', 'accountant', 'owner']]

        email_body = f"""
        This email is to notify you of Supplier: {supplier.name} with a unit price of {po_item.unit_cost},
        who has been used for purchasing: {po_item.product.name}(s).
        """
        email = EmailMessage(
            subject="Purchase Order Supplier Notification",
            body=email_body,
            from_email='admin@techcity.co.zw',
            to=modules_list('Inventory'),  
        )
        
        email.send(fail_silently=False)
        logger.info('Purchase order supplier notification email sent to: %s', recipient_list)

    for po_item in purchase_order_items:  
        logger.info("Processing purchase order item: %s", po_item)
        if po_item.unit_cost > min_price and po_item.unit_cost not in price_list:
            logger.info('Sending email for item with cost: %s', po_item.unit_cost)
            send_email(po_item)

@shared_task
def send_purchase_order_email(purchase_order_id, items_list):
    purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)

    recipient_list = [r['email'] for r in User.objects.all().values() if r['role'] in ['admin', 'accountant', 'owner']]

    m = f'Purchase Order {purchase_order.order_number}'
    message = f"{m}\n\nPurchase order Items with total cost of ${purchase_order.total_cost:2f}:\n{items_list}"

    recipient_list = ['cassymyo@gmail.com']

    send_mail(
        'Production plan creation',
        message,
        'admin@techcity.co.zw',
        recipient_list,
        fail_silently=False,
    )

    logger.info(f'Production confirmation ({purchase_order}) sent.')


@shared_task
def check_expiring_products():
    now = timezone.now()
    three_days_from_now = now + timedelta(days=3)
    
    expiring_soon = Product.objects.filter(expiry_date__range=[now, three_days_from_now])
    expired = Product.objects.filter(expiry_date__lt=now)
    
    if expiring_soon.exists() or expired.exists():
        subject = "Expiring Products Notification"
        message = "The following products are expiring soon or have expired:\n\n"
        
        if expiring_soon.exists():
            message += "Products expiring within 3 days:\n"
            for product in expiring_soon:
                message += f"{product.name} (Expiry Date: {product.expiry_date})\n"
        
        if expired.exists():
            message += "\nExpired Products:\n"
            for product in expired:
                message += f"{product.name} (Expired on: {product.expiry_date})\n"
        
        recipient_list = [r['email'] for r in User.objects.all().values()]
        
        send_mail(
            subject,
            message,
            'admin@techcity.co.zw',  
            [recipient_list],  
        )

    



        

    
    