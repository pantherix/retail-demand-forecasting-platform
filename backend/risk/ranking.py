from __future__ import annotations


class RiskScoreCalculator:
    """
    Risk Score

    0-100

    Factors:

    Inventory Coverage
    Forecast Demand
    Revenue Impact
    Stockout Probability
    """

    def calculate(self, forecast, stock, revenue):

        score = 0

        if forecast <= 0:

            return 0

        coverage = stock / forecast

        if coverage < 0.25:

            score += 40

        elif coverage < 0.50:

            score += 30

        elif coverage < 1:

            score += 15

        if revenue > 500000:

            score += 25

        elif revenue > 100000:

            score += 15

        else:

            score += 5

        stockout_probability = (forecast - stock) / forecast

        score += int(stockout_probability * 35)

        return min(score, 100)


class RiskClassifier:

    def classify(self, score):

        if score >= 80:

            return "CRITICAL"

        if score >= 60:

            return "HIGH"

        if score >= 40:

            return "MEDIUM"

        return "LOW"


class RevenueRiskAnalyzer:

    def evaluate(self, revenue, forecast):

        potential_loss = max(forecast - revenue, 0)

        return {"potential_loss": round(potential_loss, 2)}


class StockoutAnalyzer:

    def evaluate(self, stock, forecast):

        if forecast <= 0:

            return {"probability": 0}

        probability = (max(forecast - stock, 0) / forecast) * 100

        return {"probability": round(probability, 2)}


class OverstockAnalyzer:

    def evaluate(self, stock, forecast):

        if forecast <= 0:

            return {"overstock": stock}

        excess = max(stock - (forecast * 1.5), 0)

        return {"overstock": excess}


class SKURiskEngine:

    def __init__(self):

        self.scorer = RiskScoreCalculator()

        self.classifier = RiskClassifier()

        self.revenue = RevenueRiskAnalyzer()

        self.stockout = StockoutAnalyzer()

        self.overstock = OverstockAnalyzer()

    def evaluate(self, sku, forecast, stock, revenue):

        score = self.scorer.calculate(forecast, stock, revenue)

        category = self.classifier.classify(score)

        stockout = self.stockout.evaluate(stock, forecast)

        overstock = self.overstock.evaluate(stock, forecast)

        revenue_risk = self.revenue.evaluate(revenue, forecast)

        return {
            "sku": sku,
            "risk_score": score,
            "risk": category,
            "stockout": stockout,
            "overstock": overstock,
            "revenue_risk": revenue_risk,
        }


class PortfolioRiskRanking:

    def __init__(self):

        self.engine = SKURiskEngine()

    def rank(self, products):

        rankings = []

        for item in products:

            rankings.append(
                self.engine.evaluate(
                    sku=item["sku"],
                    forecast=item["forecast"],
                    stock=item["stock"],
                    revenue=item["revenue"],
                )
            )

        rankings = sorted(rankings, key=lambda x: x["risk_score"], reverse=True)

        return rankings

    def critical_only(self, products):

        ranked = self.rank(products)

        return [x for x in ranked if x["risk"] == "CRITICAL"]


risk_engine = PortfolioRiskRanking()
