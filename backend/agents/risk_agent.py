class RiskAgent:

    def execute(self, stock, forecast):

        coverage = stock / max(forecast, 1)

        if coverage < 0.25:

            level = "CRITICAL"

        elif coverage < 0.50:

            level = "HIGH"

        elif coverage < 1:

            level = "MEDIUM"

        else:

            level = "LOW"

        return {"coverage": coverage, "risk": level}
