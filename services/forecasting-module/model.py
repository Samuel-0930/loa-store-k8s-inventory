import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import warnings

warnings.filterwarnings("ignore")

class InventoryForecaster:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        # 데이터 로드 및 초기 전처리
        self.df_raw = pd.read_csv(csv_path)
        self.df_raw['date'] = pd.to_datetime(self.df_raw['date'])

    def _feature_engineering(self, df):
        """
        생산 데이터용 피처 엔지니어링 (데이터 누수 방지)
        """
        df = df.copy()
        df = df.sort_values('date')
        
        # 1. 시간 기반 피처
        df['day_of_week'] = df['date'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
        df['day_of_month'] = df['date'].dt.day
        
        # 2. Lag Features (이전 판매량)
        for lag in [1, 7, 14, 30]:
            df[f'lag_{lag}'] = df['quantity'].shift(lag)
            
        # 3. Rolling Window Features (현재 시점 T를 제외한 T-1 시점 기준 계산 - 누수 방지)
        for window in [7, 30]:
            df[f'rolling_mean_{window}'] = df['quantity'].shift(1).rolling(window=window).mean()
            df[f'rolling_std_{window}'] = df['quantity'].shift(1).rolling(window=window).std()
            
        return df.dropna()

    def predict_demand(self, item_id, days_to_predict=7):
        """
        Random Forest 모델을 사용하여 Recursive Multi-step Forecasting(재귀적 미래 예측)을 수행합니다.
        """
        # 해당 상품 데이터 필터링
        item_data = self.df_raw[self.df_raw['item_id'] == item_id].sort_values('date')
        
        # 최소 30일치 롤링 윈도우 + 학습 데이터 확보를 위해 최소 35일이 필요합니다.
        if len(item_data) < 35:
            return {"error": "예측을 위한 충분한 이력 데이터(최소 35일)가 없습니다."}

        # 1. 피처 엔지니어링 수행
        df_feat = self._feature_engineering(item_data)
        
        # 2. 학습 데이터 준비
        X = df_feat.drop(['date', 'quantity', 'item_id'], axis=1)
        y = df_feat['quantity']
        
        # 3. 벤치마킹에서 최고 성능을 기록한 Random Forest 모델 학습 (최적화 하이퍼파라미터 적용)
        model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X, y)
        
        # 4. Recursive Multi-step Forecasting (재귀적 미래 예측)
        forecast_results = []
        current_data = item_data.copy()
        
        last_date = current_data['date'].max()
        
        for i in range(days_to_predict):
            next_date = last_date + pd.Timedelta(days=i+1)
            
            # 다음 예측 시점의 가상 로우 생성
            next_row = {
                'date': next_date,
                'item_id': item_id,
                'quantity': np.nan # 예측할 빈 값
            }
            
            # 가상 로우 추가 및 임시 피처 생성
            temp_df = pd.concat([current_data, pd.DataFrame([next_row])], ignore_index=True)
            temp_df_feat = self._feature_engineering(temp_df)
            
            # 마지막 시점(예측 대상)의 피처 추출
            next_features = temp_df_feat.iloc[[-1]].drop(['date', 'quantity', 'item_id'], axis=1)
            
            # 예측 수행
            predicted_qty = max(0.0, float(model.predict(next_features)[0])) # 음수 재고 방지
            
            # 결과를 결과 리스트에 기록
            forecast_results.append(predicted_qty)
            
            # 가상 로우의 quantity를 예측된 값으로 채우고 데이터셋에 영구 반영 (다음 재귀 예측의 Lag 변수로 사용됨)
            temp_df.loc[temp_df.index[-1], 'quantity'] = predicted_qty
            current_data = temp_df
            
        return {
            "item_id": item_id,
            "forecast": forecast_results,
            "average_daily_demand": float(np.mean(forecast_results)),
            "status": "success"
        }

    def estimate_stockout_date(self, item_id, current_stock):
        """
        현재 재고가 언제 소진될지 예측합니다. (Random Forest 예측 적용)
        """
        prediction = self.predict_demand(item_id, days_to_predict=30)
        if "error" in prediction:
            return prediction
            
        forecast_values = prediction['forecast']
        cumulative_demand = np.cumsum(forecast_values)
        
        # 재고가 소진되는 날짜(index) 찾기
        stockout_day = np.where(cumulative_demand >= current_stock)[0]
        
        if len(stockout_day) > 0:
            return {
                "item_id": item_id,
                "days_until_stockout": int(stockout_day[0] + 1),
                "recommended_restock_date": int(max(1, stockout_day[0] - 2)) # 2일 전 발주 권장
            }
        else:
            return {"item_id": item_id, "days_until_stockout": ">30"}
