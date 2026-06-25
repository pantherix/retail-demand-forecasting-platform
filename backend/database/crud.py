from backend.database.models import Forecast


class ForecastRepository:

    def __init__(self, db):

        self.db = db

    def save_forecast(self, sku, forecast, confidence):

        row = Forecast(sku=sku, forecast=forecast, confidence=confidence)

        self.db.add(row)

        self.db.commit()

        return row
