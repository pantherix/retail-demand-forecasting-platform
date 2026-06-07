class SafetyStockCalculator:

    def calculate(self, demand_std, lead_time, z_score=1.65):

        return z_score * demand_std * (lead_time**0.5)
