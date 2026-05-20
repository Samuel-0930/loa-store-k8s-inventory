from fastapi import FastAPI
from pydantic import BaseModel
from model import InventoryForecaster
import os

app = FastAPI(title="로아 스토어 AI 예측 모듈")

# 데이터 경로 설정
DATA_PATH = os.getenv("DATA_PATH", "../../data/historical_sales.csv")
forecaster = InventoryForecaster(DATA_PATH)

class PredictionRequest(BaseModel):
    item_id: int
    current_stock: int

@app.get("/")
async def root():
    return {"message": "AI Forecasting Module is running"}

@app.post("/predict")
async def predict(req: PredictionRequest):
    """
    특정 상품의 재고 소진 시점을 예측하여 반환합니다.
    """
    result = forecaster.estimate_stockout_date(req.item_id, req.current_stock)
    return result
