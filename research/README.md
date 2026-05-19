# 🧪 모델 벤치마킹 및 선정 (Research)

본 폴더에는 최적의 재고 수요 예측 모델을 선정하기 위한 실험 과정이 담겨 있습니다.

## 1. 실험 설계
- **목표:** 향후 14일간의 상품 수요를 가장 정확하게 예측하는 모델 선정
- **평가 지표:** MAE(평균 절대 오차), RMSE, MAPE
- **데이터:** 180일간의 시뮬레이션 판매 데이터

## 2. 피처 엔지니어링
- **시차(Lag):** t-1, t-7, t-14
- **이동 평균(Rolling):** 7일/14일 평균 및 표준편차
- **시간 정보:** 요일, 주말, 월별 특성

## 3. 비교 모델 (Total 12)
- Baseline: Naive, SMA
- Statistical: ETS, ARIMA
- Classical ML: Linear, Ridge, Lasso, Decision Tree, Random Forest
- Boosting: XGBoost, LightGBM, CatBoost
