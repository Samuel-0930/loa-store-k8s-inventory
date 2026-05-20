FROM python:3.11-slim
WORKDIR /app
COPY services/inventory-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/inventory-worker/ .
CMD ["python", "main.py"]
