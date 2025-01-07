from inventory.models import PurchaseOrderItem

def best_price(raw_material_name):
    purchase_orders = PurchaseOrderItem.objects.filter(product__name=raw_material_name)

    supplier_prices = []
    for item in purchase_orders:
        supplier_prices.append(
            {
                'id':item.purchase_order.supplier.id,
                'supplier': item.purchase_order.supplier.name, 
                'price': item.unit_cost
            }
        )

    supplier_prices_sorted = sorted(supplier_prices, key=lambda x: x['price'])

    return supplier_prices_sorted[:3]