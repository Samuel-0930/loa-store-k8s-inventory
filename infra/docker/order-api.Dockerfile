# 파이썬 3.11 환경 기반 (경량화된 slim 버전)
FROM python:3.11-slim

# 컨테이너 내 작업 디렉토리 설정
WORKDIR /app

# 라이브러리 설치를 위해 요구사항 파일 복사 및 설치
COPY services/order-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 현재 폴더의 소스 코드를 컨테이너로 복사
COPY services/order-api/ .

# API 서버 실행 (외부 접근을 위해 host를 0.0.0.0으로 설정)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
