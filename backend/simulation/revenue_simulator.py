class RevenueSimulator:

    def simulate(self, forecast, price):

        revenue = forecast * price

        return {"forecast": forecast, "price": price, "revenue": revenue}
