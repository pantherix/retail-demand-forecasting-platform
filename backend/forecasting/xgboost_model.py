import xgboost as xgb


class XGBoostForecaster:

    def __init__(self):

        self.model = xgb.XGBRegressor(
            n_estimators=500,
            max_depth=8,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
        )

    def train(self, df):

        data = df.copy()

        data["lag1"] = data["sales"].shift(1)
        data["lag7"] = data["sales"].shift(7)
        data["lag30"] = data["sales"].shift(30)

        data = data.dropna()

        X = data[["lag1", "lag7", "lag30"]]

        y = data["sales"]

        self.model.fit(X, y)

    def predict(self, lag1, lag7, lag30):

        pred = self.model.predict([[lag1, lag7, lag30]])

        return float(pred[0])
