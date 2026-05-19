from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import json
import os

# FastAPI 애플리케이션 초기화
app = FastAPI(title="로아 스토어 주문 API")

# 환경 변수에서 Redis 설정을 가져옵니다 (쿠버네티스 서비스 이름 사용)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = 6379
REDIS_DB = 0

# Redis 클라이언트를 설정합니다.
# 이벤트 기반 아키텍처에서 메시지 브로커(전달자) 역할을 수행합니다.
try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
except Exception as e:
    print(f"Redis 연결 실패: {e}")

# 주문 데이터 구조 정의 (Pydantic 모델)
class Order(BaseModel):
    item_id: int
    quantity: int
    user_id: str

@app.get("/")
async def health_check():
    # 서버 상태를 확인하는 헬스체크 엔드포인트
    return {"status": "ok", "message": "주문 API가 정상 작동 중입니다."}

@app.post("/order")
async def create_order(order: Order):
    """
    사용자의 주문 요청을 받아 Redis 큐(Queue)에 이벤트를 저장합니다.
    실제 재고 차감 처리는 다른 서비스(Worker)에서 비동기로 이루어집니다.
    """
    order_data = order.dict()
    
    try:
        # 주문 데이터를 JSON으로 변환하여 Redis 리스트의 왼쪽에 삽입 (LPUSH)
        r.lpush("order_events", json.dumps(order_data))
        
        return {
            "status": "success",
            "message": "주문이 성공적으로 접수되었습니다. 곧 처리될 예정입니다.",
            "data": order_data
        }
    except Exception as e:
        # Redis 연결 문제 등 인프라 오류 발생 시 500 에러 반환
        raise HTTPException(status_code=500, detail=f"주문 처리 중 오류 발생: {str(e)}")
