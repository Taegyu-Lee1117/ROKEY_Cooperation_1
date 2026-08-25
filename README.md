# ROKEY Cooperation Project 1

로봇팔과 ROS2를 활용하여 주문 접수부터 아이스크림 제조까지 자동화하는 협동로봇 프로젝트입니다.

## 프로젝트 개요

사용자가 키오스크에서 아이스크림을 주문하면 백엔드가 주문 정보를 저장하고, ROS2가 주문을 전달받아 로봇팔의 제조 동작을 실행합니다.

```text
키오스크 UI
    ↓
FastAPI 백엔드
    ↓
PostgreSQL
    ↓
ROS2 주문 처리
    ↓
두산로보틱스 로봇팔
```

## 주요 기능

- 아이스크림 맛 선택 및 주문
- 주문 상태 및 재고 관리
- 관리자 페이지
- FastAPI 기반 REST API
- PostgreSQL 주문 데이터 저장
- ROS2 Action 기반 제조 요청
- 두산로보틱스 로봇팔 동작 제어
- 종이컵 파지 및 배치
- 스쿱 파지 및 아이스크림 스쿠핑

## 프로젝트 구조

```text
ROKEY_Cooperation_1/
├── README.md
├── backend/
│   ├── app/
│   ├── migrations/
│   ├── README.md
│   ├── requirements.txt
│   └── schema.sql
├── ros2/
│   └── roskin_robot/
├── src/
│   ├── ice_cream_pj/
│   └── icecream_interfaces/
└── ui_preview/
    ├── index.html
    └── admin.html
```

### `backend`

FastAPI와 PostgreSQL을 사용하여 주문, 재고 및 관리자 기능을 처리합니다.

자세한 내용은 [backend/README.md](backend/README.md)를 참고하세요.

### `src/ice_cream_pj`

두산로보틱스 로봇팔의 종이컵 및 스쿠핑 동작 코드를 관리합니다.

실행 방법과 모션 설명은 [src/ice_cream_pj/README.md](src/ice_cream_pj/README.md)를 참고하세요.

### `src/ice_cream_pj`

백엔드에서 주문을 확인하고 ROS2 작업으로 전달하는 노드를 관리합니다.

### `src/icecream_interfaces`

아이스크림 제조 요청에 사용되는 ROS2 Action 인터페이스를 관리합니다.

### `ui_preview`

사용자 주문 화면과 관리자 화면을 관리합니다.

- `index.html`: 아이스크림 주문 화면
- `admin.html`: 주문 및 재고 관리자 화면

## 개발 환경

- Ubuntu 24.04
- ROS2 Jazzy
- Python 3.12
- FastAPI
- PostgreSQL
- psycopg
- HTML
- CSS
- JavaScript
- Doosan Robotics M0609

## Git 사용 방법

이 프로젝트는 `main` 브랜치를 기준으로 개발합니다.

작업을 시작하기 전에 최신 코드를 내려받습니다.

```bash
git switch main
git pull origin main
```

작업 완료 후 자신이 수정한 파일만 확인하여 올립니다.

```bash
git status
git add 수정한_파일
git commit -m "feat: 작업 내용"
git pull --rebase origin main
git push origin main
```

여러 팀원이 동시에 같은 파일을 수정하지 않도록 작업 범위를 먼저 공유합니다.

## 주의사항

- 로봇을 처음 실행할 때는 속도를 낮춰 테스트합니다.
- DART Platform과 ROS2 로봇 제어 프로그램을 동시에 실행하지 않습니다.
- 실제 로봇의 좌표, TCP, Tool 및 디지털 I/O 설정을 확인합니다.
- `.env`와 DB 비밀번호 등 민감한 정보는 GitHub에 올리지 않습니다.
- `build/`, `install/`, `log/` 폴더는 Git에 올리지 않습니다.