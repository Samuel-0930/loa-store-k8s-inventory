# 파이썬 3.11 경량 버전 기반
FROM python:3.11-slim

WORKDIR /app

# 필수 라이브러리 사전에 설치 (C 빌드 디펜던시 필요)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 요구사항 파일 복사 및 의존성 설치 (scikit-learn 포함)
COPY services/forecasting-module/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스코드 복사
COPY services/forecasting-module/ .
COPY data/historical_sales.csv /app/data/historical_sales.csv

# API 포트 오픈 및 실행
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
