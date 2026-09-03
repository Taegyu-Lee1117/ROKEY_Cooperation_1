# Roskin Robbins

ROS 2와 두산 협동로봇을 활용한 아이스크림 제조 자동화 시스템

## 프로젝트 개요

- **목표**: 웹 주문부터 아이스크림 제조와 완성품 제공까지 이어지는 협동로봇 기반 무인 자동화 시스템 구현
- **주요 기능**: 키오스크 주문, 제조 공정 제어, 실시간 상태 표시, 관리자 모니터링 및 수동 제어
- **사용 장비**: Doosan M0609, 컵 그리퍼, 스쿱 그리퍼, 디지털 입출력 센서
- **개발 환경**: Ubuntu 24.04.4 LTS, ROS 2 Jazzy, Python 3.12, PostgreSQL 16
- **주요 기술 스택**: ROS 2, Doosan Robotics API, FastAPI, PostgreSQL, HTML/CSS/JavaScript

## 시연 영상

<div align="center">

[![Roskin Robbins 시연 영상](https://img.youtube.com/vi/kTLdnDv2gPA/hqdefault.jpg)](https://www.youtube.com/watch?v=kTLdnDv2gPA)


</div>

## 다이어그램

<div align="center">

### 시스템 아키텍처

<img src="src/system_architecture.png" alt="시스템 아키텍처" width="700">

### 공정 플로우차트

<img src="docs/flow_chart.png" alt="공정 플로우차트" width="700">

</div>

## 상세 설명

### 문제 정의

- 일반적인 협동로봇 예제는 개별 모션 실행에 집중되어 있어 주문 접수, 제조, 상태 관리까지 연결된 서비스형 자동화 사례가 부족합니다.
- 키오스크, 백엔드, 데이터베이스, ROS 2 노드가 분리되어 있으면 주문과 로봇 상태를 일관되게 관리하기 어렵습니다.
- 컵과 스쿱을 다루는 실제 제조 공정에서는 파지 확인, 힘 제어, 일시정지, 오류 처리 등 실기 환경을 고려한 제어가 필요합니다.

### 해결 방안

- 웹 키오스크와 FastAPI를 이용해 사용자 주문을 접수하고 PostgreSQL에 공정 상태를 기록합니다.
- 주문 브리지가 백엔드의 대기 주문을 ROS 2 Action Goal로 변환해 제조 서버에 전달합니다.
- 제조 서버는 컵 공급, 스쿱 파지, 아이스크림 스쿠핑, 컵 투입, 스쿱 반환, 완성품 제공 단계를 순차 실행합니다.
- ROS 2 Action Feedback을 통해 진행 상황을 백엔드와 UI에 반영합니다.
- 관리자 화면과 Service를 이용해 일시정지, 재개, 정지, 홈 이동 및 개별 공정 명령을 처리합니다.

### 주요 기능

- **키오스크 주문**: 맛 선택, 주문 접수, 제조 진행 상태와 결과 표시
- **관리자 제어**: 로봇 상태 확인, 공정 시작/정지, 수동 명령 전송
- **제조 자동화**: 컵 공급부터 완성품 제공까지 단계별 모션 실행
- **ROS 2 연동**: Action 기반 제조 요청과 Feedback, Service 기반 관리자 명령
- **데이터 관리**: 주문 이력, 오류, 로봇 상태, 관리자 명령을 PostgreSQL에 저장
- **안전 제어**: Pause/Resume/Stop, 디지털 입력 기반 파지 확인, 힘 제어 활용
- **모듈화**: 컵, 스쿱, 서빙, 공통 모션을 독립 모듈로 분리해 유지보수성 확보
- **확장성**: 새로운 맛, 공정 단계, 관리자 명령, UI 기능을 추가할 수 있는 구조

## 시스템 구성

| 구성 요소 | 역할 |
| --- | --- |
| 키오스크/관리자 UI | 주문 접수, 공정 상태 표시, 관리자 제어 |
| FastAPI | REST API와 웹 페이지 제공, 상태 전이 및 요청 검증 |
| PostgreSQL | 주문, 오류, 로봇 상태, 관리자 명령 저장 |
| `order_bridge` | HTTP 주문과 ROS 2 Action/Service 변환 |
| `make_icecream_server` | 제조 공정 오케스트레이션 및 Action Server |
| Doosan ROS 2 Driver | M0609 모션, 디지털 I/O, 힘 제어 |

## 공정 흐름

1. 사용자가 키오스크에서 맛을 선택하고 주문합니다.
2. FastAPI가 주문을 PostgreSQL에 저장합니다.
3. `order_bridge`가 가장 오래된 대기 주문을 선점합니다.
4. `/make_icecream` Action Goal을 제조 서버에 전송합니다.
5. 제조 서버가 컵 공급, 스쿱 파지, 스쿠핑, 컵 투입, 스쿱 반환, 컵 제공을 실행합니다.
6. 단계별 Feedback과 성공/실패 결과가 백엔드에 반영됩니다.
7. 키오스크와 관리자 화면이 최신 주문 및 로봇 상태를 표시합니다.

## ROS 2 인터페이스

| 종류 | 이름 | 역할 |
| --- | --- | --- |
| Action | `/make_icecream` | 아이스크림 제조 요청, 진행 Feedback, 결과 반환 |
| Service | `/dsr01/admin_command` | 관리자 수동 명령 처리 |
| Service | `/dsr01/dsr_controller2/motion/move_pause` | 로봇 일시정지 |
| Service | `/dsr01/dsr_controller2/motion/move_resume` | 로봇 동작 재개 |
| Service | `/dsr01/dsr_controller2/motion/move_stop` | 로봇 정지 |

## 주요 로봇 설정

- Robot ID: `dsr01`
- Robot Model: `m0609`
- Robot Address: `192.168.1.100:12345`
- TCP: `GripperDA_v1_A3`
- 스쿱 그리퍼: DO 1 / DI 1
- 컵 그리퍼: DO 3 / DI 3
- 그리퍼 열기: DO 2
- ROS Domain ID: `30`

> 실제 로봇 실행 전 TCP/Tool 설정, 작업 좌표, 비상정지 장치 및 주변 안전 상태를 반드시 확인해야 합니다.

## 실행 방법

### Terminal 1: PostgreSQL 및 FastAPI

```bash
sudo systemctl start postgresql

cd backend
source .venv/bin/activate
export DATABASE_URL=postgresql://icecream:icecream@127.0.0.1:5432/icecream_db

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Terminal 2: ROS 2 및 실제 로봇

```bash
export ROS_DOMAIN_ID=30
source /opt/ros/jazzy/setup.bash
source <doosan_ws>/install/setup.bash
source install/setup.bash

ros2 launch icecream_pj icecream_system.launch.py
```

### 웹 페이지

- 키오스크: <http://127.0.0.1:8000/kiosk>
- 관리자 화면: <http://127.0.0.1:8000/admin>
- 데이터베이스 조회: <http://127.0.0.1:8000/database>
- API 문서: <http://127.0.0.1:8000/docs>

## 프로젝트 구조

```text
icecream_pj/
├── backend/                    # FastAPI 및 PostgreSQL
├── docs/                       # README 이미지
├── history/                    # 이전 프로젝트 버전
├── src/
│   ├── README.md               # 제출 및 실행 안내
│   ├── DOCUMENT.md             # 시스템 상세 기술문서
│   ├── backend/                # 제출용 백엔드
│   ├── frontend/               # 키오스크 및 관리자 UI
│   ├── icecream_interfaces/    # ROS 2 Action 및 Service
│   └── icecream_pj/            # ROS 2 Python 패키지
├── ui_preview/                 # 웹 UI 미리보기
├── 협동1.mp4                   # 제조 시연 영상
└── run_system.sh               # 통합 실행 스크립트
```

## 상세 문서

- [제출 및 실행 안내](src/README.md)
- [시스템 상세 기술문서](src/DOCUMENT.md)
- [백엔드 안내](backend/README.md)
- [이전 버전 기록](history/README.md)

## 참고 자료

- [Doosan Robotics ROS 2](https://github.com/DoosanRobotics/doosan-robot2)
- [Doosan Robotics Programming Manual](https://manual.doosanrobotics.com/ko/programming-manual/3.3.0/publish/)

## 라이선스

ROS 2 패키지는 Apache License 2.0을 사용합니다.
