from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import json
import os

# FastAPI 앱 객체 생성
app = FastAPI(title="Loa Store Order API")

# 환경 변수에서 Redis 설정 로드 (Kubernetes ConfigMap/Secret 연동 고려)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = 6379
REDIS_DB = 0

# Redis 클라이언트 초기화
# 이벤트 기반 아키텍처에서 메시지 브로커 역할을 수행합니다.
try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
except Exception as e:
    print(f"Redis 연결 실패: {e}")

# 주문 요청 데이터 모델 정의
class Order(BaseModel):
    item_id: int
    quantity: int
    user_id: str

@app.get("/")
async def health_check():
    """서비스 상태 확인을 위한 헬스체크 엔드포인트"""
    return {"status": "ok", "message": "Order API is healthy"}

@app.post("/order")
async def create_order(order: Order):
    """
    사용자의 주문을 접수하고 Redis Queue에 이벤트를 발행합니다.
    실제 재고 차감은 워커(Inventory Worker)에서 비동기로 처리됩니다.
    """
    order_data = order.dict()
    
    try:
        # 이벤트를 JSON 형태로 변환하여 Redis List(Queue)에 푸시 (LPUSH)
        r.lpush("order_events", json.dumps(order_data))
        
        return {
            "status": "success",
            "message": "주문이 성공적으로 접수되었습니다.",
            "data": order_data
        }
    except Exception as e:
        # 인프라 이슈(Redis 연결 등) 발생 시 에러 반환
        raise HTTPException(status_code=500, detail=f"주문 처리 중 오류 발생: {str(e)}")
