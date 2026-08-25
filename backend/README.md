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


---

## 데이터베이스 및 시스템 흐름

# ROSKIN ROBBINS 시스템 및 데이터베이스 구조

## 문서 목적

아이스크림 키오스크에서 주문이 생성되고, FastAPI와 PostgreSQL을 거쳐 ROS 2 로봇이 작업을 수행한 뒤 UI에 결과가 반영되는 전체 구조를 설명한다.

## 핵심 요약

- 백엔드: FastAPI
- 데이터베이스: PostgreSQL (`icecream_db`)
- 로봇 통신: ROS 2 Action (`MakeIcecream`)
- 연결 노드: `order_bridge`
- 현재 테이블: `icecream_flavor`, `order_history`, `error_log`
- 주문 상태: `PENDING → PROCESSING → COMPLETED` 또는 `FAILED`

## 전체 시스템 흐름

```text
[키오스크 UI] ⇄ [FastAPI] ⇄ [PostgreSQL]
                     ⇅
               [order_bridge]
                     ⇅
            [ROS 2 Action Server]
                     ⇅
              [Doosan Robot]

[관리자 UI] ⇄ [FastAPI / ROS 2]
```

### 주문 저장 흐름

1. 사용자가 키오스크 UI에서 맛을 선택한다.
2. UI가 FastAPI의 `POST /orders`를 호출한다.
3. FastAPI가 PostgreSQL의 `order_history`에 주문을 `PENDING` 상태로 저장한다.

### 로봇 실행 흐름

1. `order_bridge`가 FastAPI에서 다음 `PENDING` 주문을 조회한다.
2. 주문을 수령하면 상태가 `PROCESSING`으로 바뀐다.
3. `order_bridge`가 ROS 2 Action Server에 `MakeIcecream` Goal을 보낸다.
4. ROS 2 Action Server가 Doosan Robot의 제조 동작을 실행한다.

### 상태 반영 흐름

1. 로봇이 ROS 2 Action feedback과 result를 반환한다.
2. `order_bridge`가 결과를 FastAPI로 전달한다.
3. FastAPI가 PostgreSQL의 주문 상태와 오류 내용을 갱신한다.
4. 키오스크 UI가 주문 상태 API를 주기적으로 조회한다.
5. UI가 진행 바와 완료 또는 실패 화면을 갱신한다.

## 1. icecream_flavor

키오스크에 표시할 아이스크림 맛과 판매 가능 여부를 저장한다.

| 컬럼 | 자료형 | 의미 | 제약 및 예시 |
|---|---|---|---|
| `id` | INTEGER | 맛 고유 번호 | Primary Key, 자동 증가 |
| `name` | VARCHAR(50) | 맛 이름 | UNIQUE, NOT NULL |
| `is_available` | BOOLEAN | 주문 가능 여부 | 기본값 `TRUE` |

기본 맛 데이터:

- 바닐라
- 초콜릿
- 딸기

## 2. order_history

고객 주문과 로봇 제조 진행 상태를 저장하는 중심 테이블이다.

| 컬럼 | 자료형 | 의미 | 제약 및 예시 |
|---|---|---|---|
| `id` | INTEGER | 주문 번호 | Primary Key, 자동 증가 |
| `flavor_id` | INTEGER | 주문한 맛 번호 | Foreign Key → `icecream_flavor.id` |
| `status` | VARCHAR(20) | 주문 처리 상태 | `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` |
| `ordered_at` | TIMESTAMPTZ | 주문 접수 시각 | 기본값 `CURRENT_TIMESTAMP` |

### 주문 상태 흐름

```text
PENDING      주문 접수 및 로봇 배정 대기
   ↓
PROCESSING   로봇 제조 작업 진행 중
   ├──→ COMPLETED   제조 완료
   └──→ FAILED      제조 실패
```

현재 UI 진행률:

| 주문 상태 | UI 표시 | 진행률 |
|---|---|---:|
| `PENDING` | 로봇 배정 대기 중 | 5% |
| `PROCESSING` | 아이스크림 제조 중 | 35% |
| `COMPLETED` | 제조 완료 | 100% |
| `FAILED` | 제조 실패 안내 | - |

## 3. error_log

어떤 주문의 어느 제조 단계에서 무슨 오류가 발생했는지 저장한다.

| 컬럼 | 자료형 | 의미 | 제약 및 예시 |
|---|---|---|---|
| `id` | INTEGER | 오류 기록 번호 | Primary Key, 자동 증가 |
| `order_id` | INTEGER | 오류가 발생한 주문 | Foreign Key → `order_history.id`, ON DELETE CASCADE |
| `process_step` | VARCHAR(50) | 오류 발생 단계 | `CUP_PICK`, `SCOOP_ICECREAM`, `SERVE_CUP` 등 |
| `error_code` | VARCHAR(50) | 오류 종류 | `GRIP_FAILED`, `MOVE_FAILED` 등 |
| `message` | VARCHAR(255) | 오류 상세 설명 | NOT NULL |
| `created_at` | TIMESTAMPTZ | 오류 발생 시각 | 기본값 `CURRENT_TIMESTAMP` |

### 제조 단계 값

- `CUP_PICK`: 컵 집기
- `CUP_PLACE`: 컵 놓기
- `SCOOP_PICK`: 스쿱 집기
- `MOVE_TO_ICECREAM`: 아이스크림 위치로 이동
- `SCOOP_ICECREAM`: 아이스크림 뜨기
- `PUT_ICECREAM_IN_CUP`: 컵에 아이스크림 담기
- `SCOOP_RETURN`: 스쿱 반환
- `SPOON_INSERT`: 스푼 삽입
- `SERVE_CUP`: 완성된 컵 제공

### 오류 코드 값

- `GRIP_FAILED`: 그립 실패
- `MOVE_FAILED`: 이동 실패
- `SCOOP_FAILED`: 스쿱 작업 실패
- `INSERT_FAILED`: 삽입 작업 실패
- `UNKNOWN_ERROR`: 분류되지 않은 오류

## 주요 API

| 메서드 | 경로 | 용도 |
|---|---|---|
| GET | `/flavors?available_only=true` | 판매 가능한 맛 조회 |
| POST | `/orders` | 새 주문 생성 |
| GET | `/orders/{order_id}` | 주문 상태 조회 |
| PATCH | `/orders/{order_id}/status` | 주문 상태 변경 |
| GET | `/robot/orders/next` | 다음 대기 주문 조회 |
| POST | `/robot/orders/{order_id}/claim` | 로봇이 주문 수령 |
| POST | `/errors` | 오류 기록 생성 |
| GET | `/orders/stats` | 주문 통계 조회 |
| GET | `/errors/stats` | 오류 통계 조회 |

## 구성 요소별 역할

| 구성 요소 | 역할 |
|---|---|
| 키오스크 UI | 맛 선택, 주문 생성, 상태 진행 바 표시 |
| 관리자 UI | 로봇 상태 확인, 제어, 운영 모니터링 |
| FastAPI | REST API 제공, 요청 검증, DB 읽기 및 쓰기 |
| PostgreSQL | 맛, 주문, 오류 데이터 영구 저장 |
| `order_bridge` | FastAPI 주문을 ROS 2 Action Goal로 변환하고 결과를 API에 반영 |
| ROS 2 Action Server | `MakeIcecream` 실행, 단계별 feedback과 최종 result 반환 |
| Doosan Robot | 컵, 스쿱, 아이스크림 제조 및 서빙 동작 수행 |

## 추후 구현할 단계별 진행률 및 로그

현재 DB에는 주문의 큰 상태인 `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`만 저장한다. 추후에는 로봇의 모든 주요 동작 단계마다 DB를 업데이트하여 실제 작업 진행 상황을 기록한다.

구현 흐름:

```text
로봇이 동작 단계 시작
→ ROS 2 Action feedback 발행
→ order_bridge가 FastAPI에 단계 전달
→ PostgreSQL에 current_step, progress, 단계 로그 저장
→ 키오스크 UI가 최신 상태 조회
→ 실제 로봇 동작에 맞춰 진행 바와 안내 문구 갱신
```

필요한 작업:

- `order_history`에 `current_step`과 `progress` 컬럼 추가
- 정상 동작 단계와 오류를 함께 기록할 `process_log` 테이블 추가 검토
- 현재 제조 단계와 진행률을 갱신하는 FastAPI 엔드포인트 추가
- 로봇의 각 동작 시작·완료 시 ROS 2 Action feedback 발행
- `order_bridge`가 feedback을 FastAPI로 전달
- FastAPI가 현재 단계, 진행률, 시작·완료 시각과 메시지를 PostgreSQL에 저장
- 키오스크 UI가 최신 값을 조회해 실제 단계 기반으로 진행 바와 상태 문구 갱신
- 관리자 UI의 System Log에 단계별 실행 기록과 오류 기록 표시

기록할 로그 예시:

- 주문 번호
- 로봇 동작 단계
- 단계 상태(`STARTED`, `COMPLETED`, `FAILED`)
- 진행률
- 로그 메시지
- 시작 시각과 완료 시각
- 오류 코드와 오류 상세 내용

예상 진행률 매핑:

| 제조 단계 | 진행률 예시 |
|---|---:|
| 컵 집기 | 10% |
| 컵 놓기 | 20% |
| 스쿱 집기 | 30% |
| 아이스크림 위치로 이동 | 45% |
| 아이스크림 뜨기 | 60% |
| 컵에 담기 | 75% |
| 스쿱 반환 | 85% |
| 스푼 삽입 | 92% |
| 컵 제공 | 100% |

## 관련 화면

- 키오스크: `http://127.0.0.1:8000/kiosk`
- 관리자 페이지: `http://127.0.0.1:8000/admin`
- DB 구조 및 흐름도: `http://127.0.0.1:8000/database`
- FastAPI 문서: `http://127.0.0.1:8000/docs`

## 현재 구현 상태

- [x] 키오스크 주문 생성
- [x] PostgreSQL 주문 저장
- [x] 주문 상태 조회 및 수동 변경
- [x] 완료 진행 바 애니메이션
- [x] FastAPI와 ROS 2 `order_bridge` 연결
- [x] DB 구조 HTML 및 전체 시스템 흐름도
- [ ] 관리자 UI와 실제 ROS 2 제어 기능 연결
- [ ] 제조 단계별 DB 업데이트
- [ ] 실제 로봇 단계 기반 UI 진행률
