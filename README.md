# 🛒 Loa Store: 실시간 재고 관리 및 AI 예측 시스템

> **Kubernetes 기반 MSA 아키텍처와 AI 시계열 분석을 결합한 스마트 이커머스 인프라 프로젝트**

## 🌟 Project Overview
본 프로젝트는 단순한 쇼핑몰 구축을 넘어, **대규모 트래픽 상황에서의 안정적인 데이터 처리**와 **AI 기반의 비즈니스 의사결정 자동화**를 목표로 합니다. 사용자의 주문 데이터를 실시간으로 수집하고, 재고 상태를 분석하여 최적의 발주 타이밍을 AI가 예측하는 End-to-End 인프라를 구축합니다.

## 🏗 System Architecture
이벤트 기반 마이크로서비스 아키텍처(Event-Driven MSA)를 채택하여 시스템의 확장성과 안정성을 확보했습니다.

1.  **Shopping Mall (Next.js)**: 사용자 인터페이스 및 주문 발생.
2.  **Order API (FastAPI)**: 주문 접수 및 Redis 메시지 큐로 이벤트 발행.
3.  **Inventory Worker (Python)**: Redis 이벤트를 소비하여 DB 재고 차감 및 분석 요청.
4.  **AI Forecasting (Prophet/ARIMA)**: 판매 트렌드 분석 및 품절 임박 알림/발주 권고 생성.
5.  **Infrastructure**: Kubernetes (Kind), Redis (Message Broker), PostgreSQL (RDBMS).

## 🚀 Key Features
- **실시간 데이터 파이프라인**: Redis Queue를 활용한 비동기 주문 처리.
- **클라우드 네이티브 설계**: Docker 및 Kubernetes Manifest를 통한 인프라 코드화(IaC).
- **자동 확장성(Scalability)**: K8s HPA를 통한 부하 기반 오토스케일링 고려.
- **AI 인사이트**: 데이터 분석 역량을 활용한 실시간 재고 예측 로직.

## 🛠 Tech Stack
- **Backend**: Python, FastAPI
- **Database**: PostgreSQL, Redis
- **Infrastructure**: Kubernetes, Docker
- **Data Science**: Facebook Prophet, Statsmodels (ARIMA)
- **CI/CD**: GitHub Actions

## 📂 Structure
- `services/`: 각 마이크로서비스 소스 코드
- `infra/`: Dockerfile 및 K8s 리소스 명세
- `.github/workflows/`: 자동화된 빌드 및 테스트 파이프라인
