from inventory.models import Product, Stock
from django.db.models import Sum

class StockEvaluationMethods:
    def __init__(self, product):
        self.product = product
        self.stock = Stock.objects.filter(product=self.product, out_of_stock=False).order_by('date')

    def fifo_cost_valuation(self, quantity_sold):
        remaining_units = quantity_sold
        total_cost = 0

        for stock_item in self.stock:
            if remaining_units <= 0:
                break
            
            if stock_item.quantity > 0:
                if stock_item.quantity > remaining_units:
                    total_cost += remaining_units * stock_item.cost
                    stock_item.quantity -= remaining_units
                    remaining_units = 0
                else:
                    total_cost += stock_item.quantity * stock_item.cost
                    remaining_units -= stock_item.quantity
                    stock_item.quantity = 0  
                
                if stock_item.quantity == 0:
                    stock_item.out_of_stock = True
                    stock_item.save()


        if remaining_units > 0:
            print(f"Not enough stock to sell {quantity_sold} quantity. Remaining: {remaining_units}")
            return total_cost 

        return total_cost


    def weighted_average_cost(self):
        total_units = self.stock.aggregate(Sum('quantity'))['quantity__sum'] or 0
        total_cost = sum(stock_item.quantity * stock_item.cost for stock_item in self.stock)

        if total_units == 0:
            return 0  
        
        average_cost = total_cost / total_units
        return average_cost



