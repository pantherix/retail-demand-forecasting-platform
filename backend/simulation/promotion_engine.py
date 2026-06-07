class PromotionEngine:

    def run(self, demand, promotion_percent):

        uplift = demand * (promotion_percent / 100)

        return {"base": demand, "promotion": uplift, "forecast": demand + uplift}
