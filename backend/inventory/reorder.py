class ReorderPlanner:

    def calculate(self, forecast, current_stock):

        safety_stock = forecast * 0.20

        reorder_point = forecast * 0.60

        recommended_order = max(forecast + safety_stock - current_stock, 0)

        return {
            "forecast": forecast,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "recommended_order": recommended_order,
        }
