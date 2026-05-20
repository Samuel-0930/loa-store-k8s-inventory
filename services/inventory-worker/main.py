import redis
import json
import time
import os
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Stock, Order, Item

# 환경변수 로드
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = 6379

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:roastore123@localhost:5432/roastore")
FORECAST_API_URL = os.getenv("FORECAST_API_URL", "http://localhost:8000/predict")

# SQLAlchemy 설정
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def call_ai_forecaster(item_id, current_stock):
    """
    AI 수요 예측 API를 호출하여 재고 소진 시점을 분석합니다.
    """
    try:
        payload = {
            "item_id": int(item_id),
            "current_stock": int(current_stock)
        }
        response = requests.post(FORECAST_API_URL, json=payload, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[-] AI API 호출 실패 (상태 코드: {response.status_code}): {response.text}")
    except Exception as e:
        print(f"[-] AI API 호출 중 예외 발생: {e}")
    return None

def process_order_event(db, order_data):
    """
    트랜잭션을 사용하여 주문 이벤트를 처리하고 재고를 차감합니다.
    """
    item_id = order_data["item_id"]
    quantity = order_data["quantity"]
    user_id = order_data["user_id"]

    print(f"[+] 주문 이벤트 처리 시작 - 상품 ID: {item_id}, 수량: {quantity}, 구매자: {user_id}")

    # 1. 새 주문 정보 DB 기록 (우선 PENDING 상태)
    new_order = Order(item_id=item_id, quantity=quantity, user_id=user_id, status="PENDING")
    db.add(new_order)
    db.flush() # ID 조회를 위해 프리-커밋

    try:
        # 2. 비관적 락(SELECT FOR UPDATE)을 이용해 동시성 안전 보장하며 재고 확인
        stock_record = db.query(Stock).filter(Stock.item_id == item_id).with_for_update().first()
        
        if not stock_record:
            print(f"[-] 오류: 상품 ID {item_id}에 대한 재고 정보가 테이블에 존재하지 않습니다.")
            new_order.status = "FAILED"
            db.commit()
            return

        # 3. 재고 차감 가능 여부 검증
        if stock_record.quantity < quantity:
            print(f"[-] 재고 부족 실패: 상품 {item_id} 현재 재고 {stock_record.quantity}개, 요청 {quantity}개")
            new_order.status = "FAILED"
            db.commit()
            return

        # 4. 재고 실차감 및 주문 완료 상태 업데이트
        stock_record.quantity -= quantity
        new_order.status = "COMPLETED"
        db.commit()
        print(f"[+] 재고 차감 완료 및 DB 트랜잭션 정상 커밋 (남은 재고: {stock_record.quantity}개)")

        # 5. AI API 비동기 연동 및 실시간 모니터링 경고 로직
        forecast_res = call_ai_forecaster(item_id, stock_record.quantity)
        if forecast_res and "days_until_stockout" in forecast_res:
            days_left = forecast_res["days_until_stockout"]
            
            # 소진 일수에 따른 지능형 알림 시뮬레이션
            if days_left == ">30":
                print(f"[ℹ️] 상품 {item_id} 예측 정보: 향후 30일 이내 소진 예상 없음 (안전)")
            else:
                days_left = int(days_left)
                rec_date = forecast_res.get("recommended_restock_date", 1)
                
                print(f"[🤖 AI 분석 결과] 상품 ID {item_id}는 약 {days_left}일 내 소진될 것으로 예상됩니다.")
                
                if days_left <= 7:
                    print(f"============================================================")
                    print(f"🚨 [경고] 상품 ID {item_id} ('{stock_record.item.name if stock_record.item else 'Unknown'}') 재고 위기 발생!")
                    print(f"⚠️  예상 소진일: {days_left}일 이내")
                    print(f"🛒 권장 재발주 예정일: {rec_date}일 이내 발주 요망 (안전 마진 확보용)")
                    print(f"============================================================")
                else:
                    print(f"[ℹ️] 상품 {item_id} 예측 정보: {days_left}일 내 소진 예정 (모니터링 유지, {rec_date}일 전 발주 권장)")

    except Exception as e:
        db.rollback()
        print(f"[-] 주문 처리 과정 중 롤백 유발 중대 오류 발생: {e}")
        try:
            # 트랜잭션 오류 시 상태 FAILED 전환
            fail_session = SessionLocal()
            stmt_order = fail_session.query(Order).filter(Order.id == new_order.id).first()
            if stmt_order:
                stmt_order.status = "FAILED"
                fail_session.commit()
            fail_session.close()
        except Exception as rollback_err:
            print(f"[-] 예외 주문 처리 상태 변경 실패: {rollback_err}")

def main():
    print(f"[*] 재고 관리 워커 프로세스가 기동되었습니다. (접속 Redis: {REDIS_HOST})")
    
    # DB 연결 확인 및 헬스 체크
    try:
        db_test = SessionLocal()
        db_test.execute("SELECT 1")
        db_test.close()
        print("[+] PostgreSQL 데이터베이스 연결 테스트 성공")
    except Exception as e:
        print(f"[-] PostgreSQL 데이터베이스 접속 불가: {e}")
        time.sleep(5)
        return

    # Redis 연결 설정
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    except Exception as e:
        print(f"[-] Redis 연결 불가: {e}")
        return

    while True:
        try:
            result = r.brpop("order_events", timeout=5)
            if result:
                _, message = result
                order_data = json.loads(message)
                
                db = SessionLocal()
                process_order_event(db, order_data)
                db.close()
        except Exception as queue_err:
            print(f"[-] 큐 메시지 핸들링 오류: {queue_err}")
            time.sleep(1)

if __name__ == "__main__":
    main()
