class ReorderPointCalculator:

    def calculate(self, avg_daily_demand, lead_time, safety_stock):

        return avg_daily_demand * lead_time + safety_stock
