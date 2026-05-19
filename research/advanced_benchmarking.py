import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.linear_model import LinearRegression, Ridge, Lasso, RidgeCV
from sklearn.ensemble import RandomForestRegressor, StackingRegressor
from sklearn.tree import DecisionTreeRegressor
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
import warnings

# 고급 모델 로드
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
    
    # 분석 대상 아이템 선정 (1번 상품)
    data = df[df['item_id'] == 1].sort_values('date')
    train, val, test = train_val_test_split(data)
    
    # ML 모델용 데이터 분할
    X_train = train.drop(['date', 'quantity', 'item_id'], axis=1)
    y_train = train['quantity']
    X_val = val.drop(['date', 'quantity', 'item_id'], axis=1)
    y_val = val['quantity']
    X_test = test.drop(['date', 'quantity', 'item_id'], axis=1)
    y_test = test['quantity']
    
    # 결합 데이터 (학습 + 검증) - HPO 및 최종 학습용
    X_train_val = pd.concat([X_train, X_val])
    y_train_val = pd.concat([y_train, y_val])
    
    results = []

    def evaluate_predictions(y_true, y_pred, model_name):
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = mean_absolute_percentage_error(y_true, y_pred)
        return {"Model": model_name, "MAE": mae, "RMSE": rmse, "MAPE": mape}

    # --- 1. Baseline Models ---
    # Naive (마지막 값 유지)
    pred_naive = np.full(len(y_test), y_train_val.iloc[-1])
    results.append(evaluate_predictions(y_test, pred_naive, "Naive (Baseline)"))

    # SMA (7d 이동 평균)
    pred_sma = np.full(len(y_test), y_train_val.tail(7).mean())
    results.append(evaluate_predictions(y_test, pred_sma, "SMA (7d)"))

    # --- 2. Statistical Models ---
    # ETS (Exponential Smoothing)
    try:
        model_ets = ExponentialSmoothing(y_train_val, seasonal_periods=7, trend='add', seasonal='add').fit()
        pred_ets = model_ets.forecast(len(y_test))
        results.append(evaluate_predictions(y_test, pred_ets, "ETS"))
    except Exception as e:
        print(f"ETS Error: {e}")

    # ARIMA
    try:
        model_arima = ARIMA(y_train_val, order=(5, 1, 0)).fit()
        pred_arima = model_arima.forecast(len(y_test))
        results.append(evaluate_predictions(y_test, pred_arima, "ARIMA"))
    except Exception as e:
        print(f"ARIMA Error: {e}")

    # --- 3. Classical ML Models ---
    ml_models = {
        "Linear Regression": LinearRegression(),
        "Ridge": Ridge(),
        "Lasso": Lasso(),
        "Decision Tree": DecisionTreeRegressor(random_state=42),
        "Random Forest (Default)": RandomForestRegressor(n_estimators=100, random_state=42)
    }

    for name, model in ml_models.items():
        try:
            model.fit(X_train_val, y_train_val)
            pred = model.predict(X_test)
            results.append(evaluate_predictions(y_test, pred, name))
        except Exception as e:
            print(f"{name} Error: {e}")

    # --- 4. Advanced Boosting Models ---
    # XGBoost
    try:
        model_xgb = XGBRegressor(n_estimators=100, learning_rate=0.05, random_state=42)
        model_xgb.fit(X_train_val, y_train_val)
        pred_xgb = model_xgb.predict(X_test)
        results.append(evaluate_predictions(y_test, pred_xgb, "XGBoost"))
    except Exception as e:
        print(f"XGBoost Error: {e}")

    # LightGBM
    try:
        model_lgbm = LGBMRegressor(n_estimators=100, learning_rate=0.05, random_state=42, verbose=-1)
        model_lgbm.fit(X_train_val, y_train_val)
        pred_lgbm = model_lgbm.predict(X_test)
        results.append(evaluate_predictions(y_test, pred_lgbm, "LightGBM"))
    except Exception as e:
        print(f"LightGBM Error: {e}")

    # --- 5. HPO & Ensemble Models ---
    # Prophet (E-commerce 표준)
    try:
        prophet_df = train[['date', 'quantity']].rename(columns={'date': 'ds', 'quantity': 'y'})
        m = Prophet(yearly_seasonality=False, weekly_seasonality=True, daily_seasonality=False)
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=len(val) + len(test))
        forecast = m.predict(future)
        pred_prophet = forecast.iloc[-(len(test)):]['yhat']
        results.append(evaluate_predictions(y_test, pred_prophet, "Prophet"))
    except Exception as e:
        print(f"Prophet Error: {e}")

    # Random Forest w/ Hyperparameter Tuning (RandomSearch)
    try:
        rf = RandomForestRegressor(random_state=42)
        param_dist = {'n_estimators': [50, 100, 200], 'max_depth': [None, 10, 20], 'min_samples_split': [2, 5]}
        tscv = TimeSeriesSplit(n_splits=3)
        rs_rf = RandomizedSearchCV(rf, param_dist, n_iter=5, cv=tscv, scoring='neg_mean_absolute_error', random_state=42)
        rs_rf.fit(X_train_val, y_train_val)
        best_rf = rs_rf.best_estimator_
        pred_rf = best_rf.predict(X_test)
        results.append(evaluate_predictions(y_test, pred_rf, "RF (Optimized)"))
    except Exception as e:
        print(f"RF (Optimized) Error: {e}")
        best_rf = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_train_val, y_train_val)

    # Stacking Ensemble
    try:
        estimators = [
            ('rf', best_rf),
            ('ridge', RidgeCV())
        ]
        try:
            estimators.append(('xgb', XGBRegressor(n_estimators=100, random_state=42)))
        except:
            pass
            
        stack_reg = StackingRegressor(estimators=estimators, final_estimator=RandomForestRegressor(n_estimators=50, random_state=42))
        stack_reg.fit(X_train_val, y_train_val)
        pred_stack = stack_reg.predict(X_test)
        results.append(evaluate_predictions(y_test, pred_stack, "Stacking Ensemble"))
    except Exception as e:
        print(f"Stacking Ensemble Error: {e}")

    return pd.DataFrame(results)

if __name__ == "__main__":
    import os
    csv_path = "data/historical_sales.csv"
    if not os.path.exists(csv_path):
        csv_path = "/app/data/historical_sales.csv"
    
    print(f"[*] 실계열 데이터 로드 중: {csv_path}")
    
    try:
        results_df = run_experiment(csv_path)
        
        # 전체 모델 결과 출력 (MAE 순 정렬)
        results_df = results_df.sort_values("MAE")
        print("\n--- [실험 결과 요약] ---")
        print(results_df.to_string(index=False))
        
        # 결과 저장
        output_path = "research/benchmark_results.csv"
        results_df.to_csv(output_path, index=False)
        print(f"\n[*] 모든 실험이 완료되었습니다. 결과 파일 저장됨: {output_path}")
    except Exception as e:
        print(f"[-] 실험 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
