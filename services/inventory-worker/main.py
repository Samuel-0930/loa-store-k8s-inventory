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

        # 5. AI API 비동기 연동 및 실시간 모니터링 경고 로직 (DB 트랜잭션 종료 후 실행하여 락 경합 방지)
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
            try:
                stmt_order = fail_session.query(Order).filter(Order.id == new_order.id).first()
                if stmt_order:
                    stmt_order.status = "FAILED"
                    fail_session.commit()
            finally:
                fail_session.close()
        except Exception as rollback_err:
            print(f"[-] 예외 주문 처리 상태 변경 실패: {rollback_err}")

def recover_processing_queue(r):
    """
    [Reliable Queue Pattern]
    시작 시 비정상 종료 등으로 'order_processing' 임시 대기열에 박혀있던 메시지들을
    안전하게 원본 'order_events' 메인 큐로 재인입시켜 유실을 방지합니다 (At-least-once 보장).
    """
    recovered_count = 0
    while True:
        # order_processing 우측 끝에서 꺼내 order_events 좌측 끝으로 다시 주입
        msg = r.rpoplpush("order_processing", "order_events")
        if not msg:
            break
        recovered_count += 1
        print(f"[⚠️ 복구] 처리 중단되었던 주문 데이터 원본 대기열로 복구 완료: {msg}")
    
    if recovered_count > 0:
        print(f"[✨ 복구 완료] 총 {recovered_count}개의 메시지가 안전하게 메인 대기열로 환류되었습니다.")

def main():
    print(f"[*] 재고 관리 워커 프로세스가 기동되었습니다. (접속 Redis: {REDIS_HOST})")
    
    # DB 연결 확인 및 헬스 체크
    try:
        db_test = SessionLocal()
        try:
            db_test.execute("SELECT 1")
            print("[+] PostgreSQL 데이터베이스 연결 테스트 성공")
        finally:
            db_test.close()
    except Exception as e:
        print(f"[-] PostgreSQL 데이터베이스 접속 불가: {e}")
        time.sleep(5)
        return

    # Redis 연결 설정
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        # 시작 전 유실 방지 복구 핸들러 작동
        recover_processing_queue(r)
    except Exception as e:
        print(f"[-] Redis 연결 불가: {e}")
        return

    while True:
        try:
            # [Reliable Queue Pattern]
            # BRPOP 대신 'brpoplpush'를 사용하여 꺼내는 동시에 원자적으로 임시 큐('order_processing')에 보관.
            # 이로써 데이터 처리 직전 크래시가 나더라도 메시지가 유실되지 않고 안전하게 보존됩니다.
            message = r.brpoplpush("order_events", "order_processing", timeout=5)
            
            if message:
                order_data = json.loads(message)
                
                # [Connection Lifecycle Management]
                # try-finally를 통해 어떤 심각한 예외상황이 일어나더라도 커넥션이 무조건 누수 없이 닫히도록 완벽히 보장합니다.
                db = SessionLocal()
                try:
                    process_order_event(db, order_data)
                    # 비즈니스 로직(DB 커밋 등)이 완전 성공 완료된 후 비로소 임시 큐에서 삭제(ACK 처리)
                    r.lrem("order_processing", 1, message)
                finally:
                    db.close()
                    
        except Exception as queue_err:
            print(f"[-] 큐 메시지 핸들링 오류: {queue_err}")
            time.sleep(1)

if __name__ == "__main__":
    main()
