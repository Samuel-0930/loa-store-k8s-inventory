# 🛒 Loa Store: AI 기반 스마트 재고 관리 인프라

본 프로젝트는 실시간 데이터 처리와 AI 분석을 결합하여 이커머스 운영을 자동화하는 Cloud-Native 인프라 구축 프로젝트입니다.

## 🧠 Phase 2: AI Forecasting Module
현재 프로젝트는 인프라 구축을 넘어 **AI 기반 수요 예측 단계**에 진입했습니다.

### 📚 학술적 배경 및 접근
- **ARIMA (AutoRegressive Integrated Moving Average)**: 전통적인 시계열 분석 기법으로, 과거 판매 추세와 변동성을 반영하여 단기 수요를 예측합니다. 본 프로젝트의 베이스라인 모델로 채택되었습니다.
- **EDA (Event-Driven Architecture)**: 대규모 트래픽 환경에서의 분석 지연을 방지하기 위해 주문 접수와 분석 로직을 Redis Queue로 분리하여 비동기 처리합니다.

### 📊 데이터 시뮬레이션
- `data/historical_sales.csv`: 실제 운영 전 단계에서 모델을 검증하기 위해 180일간의 가상 판매 데이터를 생성했습니다.
- **패턴 반영**: 주말 매출 급증(Seasonality), 상품별 성장 추세(Trend), 랜덤 노이즈를 포함하여 현실적인 시뮬레이션 환경을 구축했습니다.

## 📂 프로젝트 구조
- `services/order-api/`: 주문 접수 및 이벤트 발행
- `services/inventory-worker/`: 재고 차감 및 분석 연동
- `services/forecasting-module/`: **(New)** ARIMA 기반 재고 소진 시점 예측 API
- `infra/k8s/`: Kubernetes 배포 명세
- `data/`: 시뮬레이션 학습 데이터
