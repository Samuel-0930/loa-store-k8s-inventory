import redis
import json
import time
import os

# 인프라 설정 로드
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = 6379

def process_inventory():
    """
    Redis Queue에서 주문 이벤트를 가져와 실시간으로 재고를 처리하는 워커입니다.
    데이터 분석 모듈과의 연동을 통해 재고 예측 및 발주 로직을 실행합니다.
    """
    print(f"[*] Inventory Worker 시작됨 (Redis: {REDIS_HOST})")
    
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    except Exception as e:
        print(f"[-] Redis 연결 실패: {e}")
        return

    while True:
        # Redis List에서 오른쪽 끝의 데이터를 가져옴 (Blocking Pop)
        # 데이터가 들어올 때까지 대기하여 CPU 리소스 낭비를 방지합니다.
        _, message = r.brpop("order_events")
        
        if message:
            order = json.loads(message)
            print(f"[+] 주문 처리 중: Item {order['item_id']}, Qty {order['quantity']} (User: {order['user_id']})")
            
            # TODO: PostgreSQL DB 연동 및 실제 재고 차감 로직 추가 예정
            # TODO: 재고가 임계치 이하일 경우 AI Forecasting 모듈 호출 로직 추가 예정
            
            time.sleep(1)  # 처리 부하 시뮬레이션

if __name__ == "__main__":
    process_inventory()
