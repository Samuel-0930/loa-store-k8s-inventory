import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
import warnings

warnings.filterwarnings("ignore")

class InventoryForecaster:
    def __init__(self, csv_path):
        self.df = pd.read_csv(csv_path)
        self.df['date'] = pd.to_datetime(self.df['date'])

    def predict_demand(self, item_id, days_to_predict=7):
        """
        특정 상품의 향후 수요를 예측합니다. (ARIMA 모델 활용)
        """
        item_data = self.df[self.df['item_id'] == item_id].sort_values('date')
        if len(item_data) < 10:
            return {"error": "데이터 부족"}

        ts = item_data.set_index('date')['quantity']
        try:
            model = ARIMA(ts, order=(5, 1, 0))
            model_fit = model.fit()
            forecast = model_fit.forecast(steps=days_to_predict)
            return {"item_id": item_id, "forecast": forecast.tolist(), "status": "success"}
        except Exception as e:
            return {"error": str(e)}

    def estimate_stockout_date(self, item_id, current_stock):
        """
        현재 재고 소진 예상일 및 권장 발주일을 계산합니다.
        """
        prediction = self.predict_demand(item_id, days_to_predict=30)
        if "error" in prediction: return prediction
        
        forecast_values = prediction['forecast']
        cumulative_demand = np.cumsum(forecast_values)
        stockout_day = np.where(cumulative_demand >= current_stock)[0]
        
        if len(stockout_day) > 0:
            return {
                "item_id": item_id,
                "days_until_stockout": int(stockout_day[0] + 1),
                "recommended_restock_date": int(max(1, stockout_day[0] - 2))
            }
        return {"item_id": item_id, "days_until_stockout": ">30"}
