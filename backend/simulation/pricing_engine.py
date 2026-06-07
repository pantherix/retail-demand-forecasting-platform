class PricingEngine:

    def simulate(self, forecast, old_price, new_price):

        old_rev = forecast * old_price

        new_rev = forecast * new_price

        return {
            "old_revenue": old_rev,
            "new_revenue": new_rev,
            "difference": new_rev - old_rev,
        }
