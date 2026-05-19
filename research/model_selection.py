import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error, mean_absolute_error
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings("ignore")

def evaluate_models(csv_path):
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    
    # 1. Feature Engineering
    # 시간 기반 피처 생성 (계절성 반영)
    df['day_of_week'] = df['date'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    
    # 지연 피처 (Lags) 및 이동 평균 (Rolling Window)
    # 과거의 판매량이 미래 예측의 핵심 피처가 됩니다.
    df['lag_1'] = df.groupby('item_id')['quantity'].shift(1)
    df['rolling_mean_7'] = df.groupby('item_id')['quantity'].transform(lambda x: x.rolling(window=7).mean())
    
    df = df.dropna() # 결측치 제거
    
    # Item 1에 대해 모델 평가 진행
    item_id = 1
    data = df[df['item_id'] == item_id].sort_values('date')
    
    # Train/Test Split (마지막 14일을 테스트 데이터로 사용)
    train = data.iloc[:-14]
    test = data.iloc[-14:]
    
    results = []

    # Model A: Baseline (Simple Moving Average)
    test['pred_sma'] = train['quantity'].tail(7).mean()
    mae_sma = mean_absolute_error(test['quantity'], test['pred_sma'])
    results.append({"Model": "SMA (Baseline)", "MAE": mae_sma})

    # Model B: ARIMA
    history = [x for x in train['quantity']]
    predictions = []
    for t in range(len(test)):
        model = ARIMA(history, order=(5,1,0))
        model_fit = model.fit()
        yhat = model_fit.forecast()[0]
        predictions.append(yhat)
        history.append(test.iloc[t]['quantity'])
    
    mae_arima = mean_absolute_error(test['quantity'], predictions)
    results.append({"Model": "ARIMA", "MAE": mae_arima})

    return pd.DataFrame(results)

if __name__ == "__main__":
    print("--- 모델 성능 비교 (MAE 기준) ---")
    # 실제 실행은 환경에 따라 다를 수 있으므로 구조만 먼저 생성합니다.
