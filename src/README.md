# ROS 2 기반 아이스크림 제조 자동화 시스템

두산 협동로봇 **M0609**가 컵을 공급하고, 스쿱으로 아이스크림을 담은 뒤 완성된 컵을 제공하는 자동화 프로젝트입니다.

웹 키오스크에서 주문을 접수하고 FastAPI/PostgreSQL을 통해 주문 상태를 관리하며, ROS 2 Action과 Service를 이용해 실제 로봇 동작과 관리자 명령을 처리합니다.

상세 아키텍처, 인터페이스, 제어 로직, 안전 설계는 [기술문서](DOCUMENT.md)를 참고 부탁드립니다.

---

## 1) 시스템 설계

### 시스템 구성

- **웹 UI** (`frontend/roskin_robbins_v5.html`)
  - 키오스크: 맛 선택 및 주문 접수
  - 관리자 화면: 로봇 상태 확인, 공정 제어 및 수동 명령 전송
  - FastAPI가 단일 HTML 파일을 제공
- **FastAPI 백엔드** (`backend/app`)
  - 웹 페이지와 REST API 제공
  - 주문, 오류, 로봇 상태 및 관리자 명령 관리
  - PostgreSQL 데이터베이스 연동
- **주문/관리자 브리지** (`order_bridge`)
  - 백엔드에서 대기 중인 주문과 관리자 명령을 주기적으로 조회
  - 주문을 `/make_icecream` ROS 2 Action으로 전달
  - 일시정지, 재개, 정지 및 관리자 수동 명령을 ROS 2 Service로 전달
  - 공정 진행 상태와 처리 결과를 백엔드로 반환
- **아이스크림 제조 서버** (`make_icecream_server`)
  - `MakeIcecream` Action Server 제공
  - 컵 공급, 스쿱 파지, 아이스크림 스쿠핑, 컵 투입, 스쿱 반환 및 컵 제공 공정 수행
  - `AdminCommand` Service를 통한 관리자 수동 제어 지원
- **Doosan ROS 2 드라이버** (`dsr_bringup2`, `dsr_controller2`)
  - 실제 M0609 로봇 연결
  - 로봇 상태, 모션, 디지털 I/O 및 힘 제어 기능 제공

### 시스템 아키텍처

![시스템 아키텍처](system_architecture.png)

### ROS 2 인터페이스

- Action: `/make_icecream` (`icecream_interfaces/action/MakeIcecream`)
- Service: `/dsr01/admin_command` (`icecream_interfaces/srv/AdminCommand`)
- Doosan 제어 Service:
  - `/dsr01/dsr_controller2/motion/move_pause`
  - `/dsr01/dsr_controller2/motion/move_resume`
  - `/dsr01/dsr_controller2/motion/move_stop`

### 데이터 흐름

1. 사용자가 키오스크에서 맛을 선택하고 주문합니다.
2. FastAPI가 주문을 PostgreSQL의 `order_history`에 저장합니다.
3. `order_bridge`가 대기 주문을 조회하고 `/make_icecream` Action Goal을 전송합니다.
4. `make_icecream_server`가 컵 및 스쿱 모션 모듈을 순서대로 실행합니다.
5. Doosan ROS 2 드라이버가 실제 M0609 로봇과 디지털 I/O를 제어합니다.
6. 공정 피드백과 완료/실패 결과가 브리지를 통해 FastAPI와 DB에 반영됩니다.
7. 키오스크와 관리자 화면에 최신 주문 및 로봇 상태가 표시됩니다.

### 플로우차트

![시스템 플로우차트](flow_chart.png)

---

## 2) 운영체제 환경

현재 개발 및 실기 테스트 환경은 다음과 같습니다.

- OS: Ubuntu 24.04.4 LTS (Noble Numbat)
- ROS 2: Jazzy Jalisco
- Python: 3.12.3
- PostgreSQL: 16
- 로봇 통신 방식: Ethernet
- 로봇 기본 주소: `192.168.1.100:12345`
- ROS Domain ID: `30`

---

## 3) 사용한 장비 목록

- Doosan Robotics M0609 협동로봇
- Doosan 로봇 컨트롤러
- Ubuntu 및 ROS 2 실행용 PC
- Ethernet 어댑터 및 케이블
- 컵 파지용 그리퍼
- 스쿱 파지용 그리퍼
- 아이스크림 스쿱
- 종이컵 및 컵 공급부
- 아이스크림 용기와 작업대
- 디지털 입출력 기반 솔레노이드 및 파지 확인 센서

코드의 주요 로봇 설정은 다음과 같습니다.

- Robot ID: `dsr01`
- Robot Model: `m0609`
- TCP: `GripperDA_v1_A3`
- 스쿱 그리퍼 출력/입력: DO 1 / DI 1
- 컵 그리퍼 출력/입력: DO 3 / DI 3
- 그리퍼 열기 출력: DO 2

> 실제 로봇 실행 전에 TCP/Tool 설정, 작업 좌표, 비상정지 장치 및 주변 안전 상태를 반드시 확인합니다.

---

## 4) 의존성

이 문서에서 `<workspace>`는 제출받은 `src` 폴더를 넣은 ROS 2 워크스페이스, `<doosan_ws>`는 `doosan-robot2`를 빌드한 워크스페이스를 의미합니다.

### Python 패키지 (`src/backend/requirements.txt`)

```txt
fastapi>=0.115,<1.0
uvicorn[standard]>=0.34,<1.0
psycopg[binary]>=3.2,<4.0
```

설치 방법:

```bash
cd <workspace>/src/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### PostgreSQL 초기화

PostgreSQL 사용자와 `icecream_db` 데이터베이스를 준비한 후 스키마를 적용합니다. 아래 접속 정보는 프로젝트 기본 예시이며 운영 환경에서는 변경합니다.

```bash
cd <workspace>/src/backend
export DATABASE_URL='postgresql://icecream:icecream@127.0.0.1:5432/icecream_db'
PGPASSWORD=icecream psql -h 127.0.0.1 -U icecream -d icecream_db -f schema.sql
```

### ROS 2 패키지

- `rclpy`
- `action_msgs`
- `ament_index_python`
- `launch`, `launch_ros`
- `icecream_interfaces`
- `dsr_bringup2`
- `dsr_common2`
- `dsr_msgs2`
- `python3-requests`
- `rosidl_default_generators`
- `rosidl_default_runtime`

두산 ROS 2 패키지는 아래 워크스페이스에 빌드되어 있다고 가정합니다.

```text
<doosan_ws>
```

---

## 5) 실행 순서

### 최초 실행 또는 ROS 코드 변경 후 빌드

```bash
cd <workspace>

source /opt/ros/jazzy/setup.bash
source <doosan_ws>/install/setup.bash

colcon build \
  --packages-select icecream_interfaces icecream_pj \
  --symlink-install

source install/setup.bash
```

`AdminCommand.srv` 같은 ROS 인터페이스를 변경한 경우에는 인터페이스 패키지를 먼저 깨끗하게 빌드합니다.

```bash
colcon build \
  --packages-select icecream_interfaces \
  --cmake-clean-cache

source install/setup.bash
colcon build --packages-select icecream_pj --symlink-install
```

### 기본 실행: 터미널 2개

#### 터미널 1 — PostgreSQL 및 FastAPI

```bash
sudo systemctl start postgresql

cd <workspace>/src/backend
source .venv/bin/activate
export DATABASE_URL='postgresql://icecream:icecream@127.0.0.1:5432/icecream_db'

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

정상 실행 메시지:

```text
Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

#### 터미널 2 — 실제 로봇 및 주요 ROS 2 코드

```bash
cd <workspace>

export ROS_DOMAIN_ID=30
source /opt/ros/jazzy/setup.bash
source <doosan_ws>/install/setup.bash
source install/setup.bash

ros2 launch icecream_pj icecream_system.launch.py
```

`src/icecream_pj/launch/icecream_system.launch.py`의 실행 순서는 다음과 같습니다.

1. Doosan M0609 bringup 및 RViz 실행
2. 8초 후 `make_icecream_server` 실행
3. 10초 후 `order_bridge` 실행

통합 launch 대신 노드를 개별 점검할 때는 각 터미널에서 환경을 source한 후 다음 명령을 순서대로 실행할 수 있습니다.

```bash
ros2 launch dsr_bringup2 dsr_bringup2_rviz.launch.py \
  mode:=real host:=192.168.1.100 port:=12345 model:=m0609 name:=dsr01

ros2 run icecream_pj make_icecream_server
ros2 run icecream_pj order_bridge --ros-args -p api_url:=http://127.0.0.1:8000
```

ROS launch 파일은 FastAPI나 PostgreSQL을 실행하지 않습니다. 터미널 1을 먼저 실행한 후 터미널 2를 실행하며, 두 터미널은 종료하지 않고 유지합니다.

### 웹 링크

사용자/관리자 화면:

- 키오스크: <http://127.0.0.1:8000/kiosk>
- 관리자 화면: <http://127.0.0.1:8000/admin>
- 관리자 PIN: `1234`

개발/점검용 주소:

- 데이터베이스 조회 화면: <http://127.0.0.1:8000/database>
- API 문서: <http://127.0.0.1:8000/docs>
- 상태 확인 API: <http://127.0.0.1:8000/health>

### 종료 순서

1. 터미널 2에서 `Ctrl+C`를 눌러 ROS 2 노드와 로봇 연결을 종료합니다.
2. 터미널 1에서 `Ctrl+C`를 눌러 FastAPI를 종료합니다.
3. PostgreSQL을 종료해야 하는 경우에만 다음 명령을 실행합니다.

```bash
sudo systemctl stop postgresql
```
---

## 6) 제출 디렉터리 구조

```text
src/
├── README.md                    # 프로젝트 안내
├── DOCUMENT.md                  # 시스템 구조와 구현 상세 기술문서
├── system_architecture.png       # 시스템 구성도
├── flow_chart.png               # 시스템 플로우차트
├── backend/
│   ├── app/                     # FastAPI API 및 웹 서버
│   ├── migrations/              # 데이터베이스 변경 이력
│   ├── requirements.txt         # Python 의존성
│   └── schema.sql               # PostgreSQL 전체 스키마
├── frontend/
│   └── roskin_robbins_v5.html   # 키오스크 및 관리자 UI
├── icecream_interfaces/         # Action 및 Service 인터페이스
└── icecream_pj/                 # ROS 2 Python 패키지
    ├── icecream_pj/             # 제조 서버, 브리지, 모션 코드
    ├── launch/                  # 통합 launch 파일
    ├── resource/                # ament 패키지 인덱스 마커
    ├── package.xml
    ├── setup.cfg
    └── setup.py
```

---

## 라이선스

ROS 2 패키지는 Apache License 2.0을 사용합니다.
