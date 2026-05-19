
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
import warnings

# 현업에서 많이 쓰이는 부스팅 모델 (설치 필요: pip install xgboost lightgbm)
try:
    from xgboost import XGBRegressor
    from lightgbm import LGBMRegressor
except ImportError:
    print("[!] XGBoost 또는 LightGBM이 설치되어 있지 않습니다. 기본 ML 모델로 대체합니다.")

warnings.filterwarnings("ignore")

def feature_engineering(df):
    """
    전문적인 시계열 피처 엔지니어링을 수행합니다.
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['item_id', 'date'])
    
    # 1. 시간 기반 피처
    df['day_of_week'] = df['date'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    df['month'] = df['date'].dt.month
    df['day_of_year'] = df['date'].dt.dayofyear
    
    # 2. 시차 변수 (Lag Features) - 과거의 흐름 반영
    for lag in [1, 7, 14]:
        df[f'lag_{lag}'] = df.groupby('item_id')['quantity'].shift(lag)
        
    # 3. 이동 평균 변수 (Rolling Features) - 트렌드 반영
    for window in [7, 14]:
        df[f'rolling_mean_{window}'] = df.groupby('item_id')['quantity'].transform(lambda x: x.rolling(window=window).mean())
        df[f'rolling_std_{window}'] = df.groupby('item_id')['quantity'].transform(lambda x: x.rolling(window=window).std())
        
    return df.dropna()

def benchmark_models(csv_path):
    df_raw = pd.read_csv(csv_path)
    df = feature_engineering(df_raw)
    
    # 상품 1번을 기준으로 벤치마킹 진행
    data = df[df['item_id'] == 1].sort_values('date')
    train = data.iloc[:-14] # 마지막 2주를 테스트로 사용
    test = data.iloc[-14:]
    
    X_train = train.drop(['date', 'quantity', 'item_id'], axis=1)
    y_train = train['quantity']
    X_test = test.drop(['date', 'quantity', 'item_id'], axis=1)
    y_test = test['quantity']
    
    results = []

    # --- 1. Statistical / Baseline Models ---
    # 1. Naive
    test['pred_naive'] = train['quantity'].iloc[-1]
    # 2. SMA (7d)
    test['pred_sma'] = train['quantity'].tail(7).mean()
    # 3. ETS
    model_ets = ExponentialSmoothing(train['quantity'], seasonal_periods=7, trend='add', seasonal='add').fit()
    test['pred_ets'] = model_ets.forecast(len(test))
    # 4. ARIMA
    model_arima = ARIMA(train['quantity'], order=(5, 1, 0)).fit()
    test['pred_arima'] = model_arima.forecast(len(test))

    # --- 2. Classical ML Models ---
    ml_models = {
        "Linear Regression": LinearRegression(),
        "Ridge": Ridge(),
        "Lasso": Lasso(),
        "Decision Tree": DecisionTreeRegressor(),
        "Random Forest": RandomForestRegressor(n_estimators=100)
    }
    
    for name, model in ml_models.items():
        model.fit(X_train, y_train)
        test[f'pred_{name}'] = model.predict(X_test)

    # --- 3. Boosting Models (Optional) ---
    try:
        model_xgb = XGBRegressor(n_estimators=100, learning_rate=0.05).fit(X_train, y_train)
        test['pred_XGBoost'] = model_xgb.predict(X_test)
        model_lgbm = LGBMRegressor(n_estimators=100, learning_rate=0.05).fit(X_train, y_train)
        test['pred_LightGBM'] = model_lgbm.predict(X_test)
    except:
        pass

    # 성능 평가 (Evaluation)
    pred_cols = [c for c in test.columns if c.startswith('pred_')]
    for col in pred_cols:
        model_name = col.replace('pred_', '')
        mae = mean_absolute_error(y_test, test[col])
        rmse = np.sqrt(mean_squared_error(y_test, test[col]))
        mape = mean_absolute_percentage_error(y_test, test[col])
        results.append({"Model": model_name, "MAE": mae, "RMSE": rmse, "MAPE": mape})
        
    return pd.DataFrame(results).sort_values('MAE')

if __name__ == "__main__":
    print("[*] 12개 모델 성능 벤치마킹을 시작합니다...")
    # csv_path = "../data/historical_sales.csv"
    # res = benchmark_models(csv_path)
    # print(res)
