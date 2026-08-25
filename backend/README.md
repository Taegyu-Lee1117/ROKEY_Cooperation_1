# Robot Ice Cream Backend

FastAPI가 `psycopg`로 PostgreSQL에 직접 SQL을 실행하는 백엔드입니다.

## 1. PostgreSQL 준비

```bash
sudo systemctl enable --now postgresql
sudo -u postgres psql
```

`psql` 안에서 사용자와 DB를 생성합니다.

```sql
CREATE USER icecream WITH PASSWORD 'icecream';
CREATE DATABASE icecream_db OWNER icecream;
\q
```

스키마와 초기 맛 데이터를 생성합니다.

```bash
cd /home/dexy/ws_cobot_pjt/ice_cream_pj/backend
PGPASSWORD=icecream psql -h 127.0.0.1 -U icecream -d icecream_db -f schema.sql
```

## 2. API 실행

```bash
cd /home/dexy/ws_cobot_pjt/ice_cream_pj/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql://icecream:icecream@127.0.0.1:5432/icecream_db'
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API 문서: `http://127.0.0.1:8000/docs`
- 상태 확인: `http://127.0.0.1:8000/health`
- 키오스크 판매 가능 맛: `GET /flavors?available_only=true`
- 로봇의 다음 주문 조회: `GET /robot/orders/next`
- 로봇의 주문 수령: `POST /robot/orders/{order_id}/claim`

주문 상태는 `PENDING -> PROCESSING -> COMPLETED` 순서로 변경되며,
오류가 발생하면 `FAILED`로 변경합니다.

운영 환경에서는 예제 비밀번호를 반드시 변경하고 `DATABASE_URL`을 별도로 관리합니다.
