class InventoryAgent:

    def execute(self, forecast, stock):

        safety_stock = forecast * 0.2

        reorder_point = forecast * 0.6

        order_qty = max(forecast + safety_stock - stock, 0)

        return {
            "forecast": forecast,
            "stock": stock,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "recommended_order": order_qty,
        }
