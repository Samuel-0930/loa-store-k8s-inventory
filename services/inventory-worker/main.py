import redis
import json
import time
import os

# 환경 변수에서 Redis 접속 정보를 읽어옵니다.
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = 6379

def process_inventory():
    """
    Redis 큐에서 주문 이벤트를 실시간으로 가져와 처리하는 워커 프로세스입니다.
    """
    print(f"[*] 재고 관리 워커가 시작되었습니다. (접속 Redis: {REDIS_HOST})")
    
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    except Exception as e:
        print(f"[-] Redis 연결 실패: {e}")
        return

    while True:
        # Redis 리스트에서 오른쪽 끝 데이터를 가져올 때까지 대기 (BRPOP)
        # 데이터가 없을 때는 대기 상태를 유지하여 CPU 자원을 절약합니다.
        result = r.brpop("order_events")
        
        if result:
            _, message = result
            order = json.loads(message)
            print(f"[+] 주문 처리 중: 상품 ID {order['item_id']}, 수량 {order['quantity']} (사용자: {order['user_id']})")
            
            # TODO: PostgreSQL 데이터베이스에 접속하여 실제 재고 수량 차감 로직 구현 예정
            # TODO: AI 분석 모듈을 호출하여 재고 부족 여부 판단 로직 추가 예정
            
            time.sleep(1)  # 주문 처리 과정을 시뮬레이션하기 위한 짧은 지연

if __name__ == "__main__":
    process_inventory()
