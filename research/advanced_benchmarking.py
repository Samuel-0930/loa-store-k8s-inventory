
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor, StackingRegressor
from sklearn.linear_model import RidgeCV, LassoCV
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
import warnings

# 고급 모델 로드 (설치 필요: pip install xgboost lightgbm prophet)
try:
    from xgboost import XGBRegressor
    from lightgbm import LGBMRegressor
    from prophet import Prophet
except ImportError:
    pass

warnings.filterwarnings("ignore")

def advanced_feature_engineering(df):
    """
    시계열 데이터 누수(Data Leakage)를 방지하며 피처를 생성합니다.
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['item_id', 'date'])
    
    # 1. Temporal Features (Time Index)
    df['day_of_week'] = df['date'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    df['day_of_month'] = df['date'].dt.day
    
    # 2. Lag Features (과거 데이터만 사용 - 누수 방지 핵심)
    for lag in [1, 7, 14, 30]:
        df[f'lag_{lag}'] = df.groupby('item_id')['quantity'].shift(lag)
        
    # 3. Rolling Window (Window Statistics)
    for window in [7, 30]:
        # shift(1)을 통해 현재 시점의 정답이 윈도우 계산에 포함되지 않도록 함 (Leakage 방지)
        df[f'rolling_mean_{window}'] = df.groupby('item_id')['quantity'].shift(1).transform(lambda x: x.rolling(window=window).mean())
        df[f'rolling_std_{window}'] = df.groupby('item_id')['quantity'].shift(1).transform(lambda x: x.rolling(window=window).std())
        
    return df.dropna()

def train_val_test_split(df, train_ratio=0.7, val_ratio=0.15):
    """
    시계열 순서를 보존하여 70/15/15 비율로 데이터를 분할합니다.
    """
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    train = df.iloc[:train_end]
    val = df.iloc[train_end:val_end]
    test = df.iloc[val_end:]
    
    return train, val, test

def run_experiment(csv_path):
    df_raw = pd.read_csv(csv_path)
    df = advanced_feature_engineering(df_raw)
    
    # 분석 대상 아이템 선정
    data = df[df['item_id'] == 1].sort_values('date')
    train, val, test = train_val_test_split(data)
    
    X_train = train.drop(['date', 'quantity', 'item_id'], axis=1)
    y_train = train['quantity']
    X_val = val.drop(['date', 'quantity', 'item_id'], axis=1)
    y_val = val['quantity']
    X_test = test.drop(['date', 'quantity', 'item_id'], axis=1)
    y_test = test['quantity']
    
    results = []

    # --- 1. Prophet (E-commerce 표준) ---
    try:
        prophet_df = train[['date', 'quantity']].rename(columns={'date': 'ds', 'quantity': 'y'})
        m = Prophet(yearly_seasonality=False, weekly_seasonality=True, daily_seasonality=False)
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=len(val) + len(test))
        forecast = m.predict(future)
        pred_prophet = forecast.iloc[-(len(test)):]['yhat']
        results.append({"Model": "Prophet", "MAE": mean_absolute_error(y_test, pred_prophet)})
    except:
        pass

    # --- 2. Random Forest w/ Hyperparameter Tuning (RandomSearch) ---
    rf = RandomForestRegressor(random_state=42)
    param_dist = {'n_estimators': [50, 100, 200], 'max_depth': [None, 10, 20], 'min_samples_split': [2, 5]}
    # TimeSeriesSplit을 사용하여 시계열 교차 검증
    tscv = TimeSeriesSplit(n_splits=3)
    rs_rf = RandomizedSearchCV(rf, param_dist, n_iter=5, cv=tscv, scoring='neg_mean_absolute_error')
    rs_rf.fit(pd.concat([X_train, X_val]), pd.concat([y_train, y_val]))
    best_rf = rs_rf.best_estimator_
    pred_rf = best_rf.predict(X_test)
    results.append({"Model": "RF (Optimized)", "MAE": mean_absolute_error(y_test, pred_rf)})

    # --- 3. Stacking Ensemble (현업 끝판왕) ---
    # 여러 우수한 모델의 예측치를 다시 학습 모델의 입력으로 사용
    estimators = [
        ('rf', best_rf),
        ('ridge', RidgeCV())
    ]
    try:
        estimators.append(('xgb', XGBRegressor(n_estimators=100)))
    except:
        pass
        
    stack_reg = StackingRegressor(estimators=estimators, final_estimator=RandomForestRegressor(n_estimators=50))
    stack_reg.fit(pd.concat([X_train, X_val]), pd.concat([y_train, y_val]))
    pred_stack = stack_reg.predict(X_test)
    results.append({"Model": "Stacking Ensemble", "MAE": mean_absolute_error(y_test, pred_stack)})

    # ... 추가 10개 모델 생략 및 결과 반환 로직 ...
    return pd.DataFrame(results)

if __name__ == "__main__":
    print("[*] 고도화된 모델 실험 파이프라인 가동...")
