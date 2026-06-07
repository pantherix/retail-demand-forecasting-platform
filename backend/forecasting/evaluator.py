from sklearn.metrics import mean_absolute_percentage_error


def evaluate(y_true, y_pred):

    mape = mean_absolute_percentage_error(y_true, y_pred) * 100

    return {"mape": round(mape, 2)}
