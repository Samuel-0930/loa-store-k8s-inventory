FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for LightGBM, XGBoost and Prophet
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pandas numpy scikit-learn statsmodels xgboost lightgbm prophet

COPY . .
CMD ["python", "research/advanced_benchmarking.py"]
