from utils.email import EmailThread
from . models import (
    Production, 
    Transfer,
    Supplier,
    PurchaseOrderItem
)
from django.core.mail import EmailMessage
from utils.supplier_best_price import best_price
from loguru import logger
from settings.models import NotificationEmails
from utils.email_notification import modules_list

# def send_end_of_day_report(buffer):
#     email = EmailMessage(
#         f"End of Day Report:",
#         "Please find the attached End of Day report. The expected amount is to be calculated on cost price, since they are no stipulated prices per dishes, but if they to be put the expected table will be relavant.",
#         'admin@techcity.co.zw',
#         ['mirackletec@gmail.com'],
#     )
#     email.attach(f'EndOfDayReport.pdf', buffer.getvalue(), 'application/pdf')
    
#     EmailThread(email).start()

#     logger.info(f' End of day report email sent.')
 

def send_production_creation_notification(production_id):
    production = Production.objects.get(id=production_id)
    
    email = EmailMessage(
        subject=f"Production Plan Creation",
        body=f"""
        The email is to notify you on the creation of a Production Plan {production.production_plan_number}, and it requires your cornifimation.
        """,
        from_email='admin@techcity.co.zw',
        to=['mirackletec@gmail.com'],
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
        to=['mirackletec@gmail.com'],
    )
    
    EmailThread(email).start()
    
    logger.info(f'Notification for transfer {transfer.transfer_number} sent.')

def supplier_email(supplier_id, purchase_order_item):
    purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order_item.purchase_order)
    supplier = Supplier.objects.get(id=supplier_id)

    price_list = [ sup['price'] for sup in best_price(purchase_order_item.product.name)]

    min_price = min(price_list)

    def send_email(purchase_order_item):
        logger.info(modules_list('Inventory'))
        email = EmailMessage(
            subject="Purchase Order Supplier notification",
            body=f"""
            This email is to notify you of a Supplier: {supplier.name} with a unit price of {po_item.unit_cost},
            Has been used for purchasing: {purchase_order_item.product.name}(s). 
            """,
            from_email='admin@techcity.co.zw',
            to=modules_list('Inventory'),
        )
        
        EmailThread(email).start()

        logger.info(f'Purchase order supplier notification email sent.')
    
    for po_item in purchase_order_items:  
        logger.info(po_item)
        if po_item.unit_cost > min_price and po_item.unit_cost not in price_list:
            logger.info('here')
            send_email(purchase_order_item)

    



        

    
    