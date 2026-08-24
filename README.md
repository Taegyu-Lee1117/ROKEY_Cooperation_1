# ROKEY-Team-Project
ROKEY Collaboration Project 1

---

## 🍨 스쿠핑 모션 최종 스크립트 + 통합 인수인계 문서

> 작성일: 2026-08-24 · 대상: ROKEY A-3조 전원 (특히 종이컵 파지 담당자)

---

### 1. 지금까지 검증된 것

DART Platform 실기 테스트로 아래 전 구간이 **실제모드에서 동작 확인 완료**됐습니다.

```
스쿱 파지 → 통 진입 → 힘 감지 압착(벽 밀기) → 후퇴+회전(J5 감소, 위 보기)
→ 상승 → 배출 위치 이동 → 툴 120도 회전 배출 → 스쿱 반납
```

핵심 성과:
- **힘 기반 벽 압착 감지**가 정상 동작 확인 (`Fx ≤ -6N`에서 정지)
- **X+ 이동과 J5 회전을 동시에 수행**하며 재료를 충전하는 굴삭기식 스쿠핑 검증
- 오일러각(ZYZ) 이중표현 문제, 손목 특이점, 작업영역 초과 등 **총 7건의 도달 불가 오류**를 원인 분석 후 해결
- `task_compliance_ctrl`의 강성(stiffness) 설정 오류(전 축 고강성 → 힘 제한이 전혀 안 걸리던 문제) 발견 및 수정

---

### 2. 최종 스크립트 (함수 모듈화)

팀원 코드와 결합하기 쉽도록 **개별 함수로 분리**했습니다. `main()`에서 순서대로 호출하는 구조입니다.

```python
# ═══════════════════════════════════════════════════
#  아이스크림 스쿠핑 모션 - 최종본
#  담당: 도윤 (스쿱 파지 ~ 배출)
# ═══════════════════════════════════════════════════

set_tcp("GripperDA_v1_A3")

# ── 좌표 (전부 실기 검증 완료) ──────────────────────
P_HOME = posx(367.48, 3.07, 213.43, 89.68, 179.98, 90.19)

P_SC_APP = posx(607.86, 115.34, 265.02, 62.45, 178.05, 63.29)
P_SC = posx(607.86, 115.34, 145.02, 62.45, 178.05, 63.29)
P_SC_UP = posx(607.86, 115.34, 245.02, 62.45, 178.05, 63.29)

P_EN_APP = posx(366.75, -157.79, 275.00, 0.07, -143.31, 1.13)
P_EN = posx(366.75, -157.79, 125.00, 0.07, -143.31, 1.13)

P_PUSH1 = posx(397.30, -157.79, 125.00, -179.62, 173.74, -178.55)
P_PUSH2 = posx(406.02, -157.79, 125.00, -0.96, 177.56, 0.11)
P_PUSH3 = posx(414.75, -157.79, 125.00, -0.21, 168.87, 0.87)
P_PUSH4 = posx(423.48, -157.79, 125.00, -0.12, 160.17, 0.96)
P_PUSH5 = posx(432.20, -157.79, 125.00, -0.08, 151.48, 1.00)
P_PUSH6 = posx(438.66, -157.79, 125.00, -0.06, 145.06, 1.02)
P_PUSH7 = posx(445.11, -157.79, 125.00, -0.05, 138.65, 1.04)

P_BACK1 = posx(387.64, -157.79, 230.00, -0.05, 133.00, 1.04)
P_RISE = posx(346.75, -157.79, 318.34, -0.04, 108.00, 1.06)

# ★ P_POUR: 팀원의 종이컵 최종 위치와 맞춰 재검증 필요 (5절 참조)
P_POUR = posx(680.09, -238.02, 322.16, 0.42, 104.43, 1.08)

SOL = 2
WAIT_SETTLE = 2.0
WAIT_WALL = 0.7
WAIT_DROP = 1.5

F_WALL_TARGET = -6.0
F_WALL_TARGET_ABS = 6.0
F_HARD_LIMIT = 20.0
POUR_ANGLE = 120

SPEED_TRANSPORT_L = 60      # 일반 이송 (선형)
SPEED_TRANSPORT_J = 40      # 일반 이송 (관절)
SPEED_PUSH = 12             # 힘 감지 구간 - 반드시 저속 유지
SPEED_RETREAT = 40          # 후퇴~상승 (힘 감지 불필요, 빠르게 가능)


# ── 그리퍼 제어 ──────────────────────────────────────
def grip_close():
    set_digital_output(2, OFF)
    set_digital_output(3, OFF)
    wait(0.05)
    set_digital_output(1, ON)
    wait(0.8)


def grip_open():
    set_digital_output(1, OFF)
    set_digital_output(3, OFF)
    wait(0.05)
    set_digital_output(2, ON)
    wait(0.8)


def force_base():
    return get_tool_force(ref=DR_BASE)


def emergency_check(f):
    if f[0] <= -F_HARD_LIMIT or f[2] <= -F_HARD_LIMIT or f[2] >= F_HARD_LIMIT:
        tp_log("!! 비상: 힘 한계(20N) 초과 " + str(f))
        release_force()
        release_compliance_ctrl()
        return 1
    return 0


def check_wall(step_label):
    f = force_base()
    tp_log(step_label + " Fx=" + str(f[0]) + " Fy=" + str(f[1]) + " Fz=" + str(f[2]))

    if emergency_check(f) == 1:
        return 2
    if f[0] <= F_WALL_TARGET:
        tp_log(step_label + " : Fx 조건으로 정지")
        return 1
    if f[1] >= F_WALL_TARGET_ABS or f[1] <= -F_WALL_TARGET_ABS:
        tp_log(step_label + " : Fy 조건으로 정지")
        return 1
    if f[2] >= F_WALL_TARGET_ABS or f[2] <= -F_WALL_TARGET_ABS:
        tp_log(step_label + " : Fz 조건으로 정지")
        return 1
    return 0


# ── 모션 함수 ────────────────────────────────────────
def go_home():
    set_velj(SPEED_TRANSPORT_J)
    set_accj(60)
    movejx(P_HOME, sol=SOL)


def pick_scoop():
    """스쿱 거치대에서 파지, 인출 완료 상태까지."""
    set_velx(SPEED_TRANSPORT_L, 40)
    set_accx(100, 60)
    grip_open()

    movejx(P_SC_APP, sol=SOL)

    set_velx(25, 15)
    movel(P_SC)

    grip_close()
    if get_digital_input(1) == OFF:
        tp_log("!! 스쿱 파지 확인 신호 없음")

    movel(P_SC_UP)
    wait(0.3)
    # set_tool("Scoop_Tool")  # ★ 실측 후 등록 (2절 참고)


def return_scoop():
    """스쿱을 거치대에 반납."""
    set_velx(SPEED_TRANSPORT_L, 40)
    movejx(P_SC_APP, sol=SOL)
    set_velx(25, 15)
    movel(P_SC)
    grip_open()
    movel(P_SC_APP)


def scoop_one_cycle(pour_target):
    """
    스쿱 1회 사이클: 진입 -> 힘감지 압착 -> 후퇴+회전 -> 상승
    -> 지정 위치(pour_target)로 이동 -> 배출.
    pour_target: posx, 종이컵 상단 배출 위치 (팀원 좌표와 연동)
    """
    set_velx(SPEED_TRANSPORT_L, 40)
    movejx(P_EN_APP, sol=SOL)

    set_velx(25, 15)
    movel(P_EN)
    wait(0.2)

    # -- 힘 감지 압착 (X만 연성화) --
    task_compliance_ctrl(stx=[400, 3000, 3000, 3000, 3000, 3000])
    wait(0.1)
    set_desired_force(fd=[3, 0, 0, 0, 0, 0], dir=[1, 0, 0, 0, 0, 0], mod=DR_FC_MOD_REL)
    wait(0.1)

    set_velx(SPEED_PUSH, 8)
    movel(P_PUSH1)
    wait(0.15)
    f0 = force_base()
    if emergency_check(f0) == 1:
        return 0

    push_points = [P_PUSH2, P_PUSH3, P_PUSH4, P_PUSH5, P_PUSH6, P_PUSH7]
    j = 0
    while j < 6:
        movel(push_points[j])
        wait(0.15)
        result = check_wall("PUSH_STEP" + str(j + 2))
        if result == 2:
            return 0
        if result == 1:
            break
        j = j + 1

    release_force()
    wait(0.2)
    release_compliance_ctrl()
    wait(0.2)

    wait(WAIT_WALL)

    # -- 후퇴 + 회전 (재료 이탈 + 위 보기 자세) --
    set_velx(SPEED_RETREAT, 25)
    movel(P_BACK1)

    set_velx(SPEED_RETREAT, 25)
    movel(P_RISE)

    wait(WAIT_SETTLE)

    # -- 배출 위치로 이동 --
    set_velx(SPEED_TRANSPORT_L, 40)
    movel(pour_target)
    wait(0.3)

    set_velj(90)
    set_accj(120)
    movej(posj(0, 0, 0, 0, 0, -POUR_ANGLE), mod=DR_MV_MOD_REL)
    wait(WAIT_DROP)

    set_velj(30)
    set_accj(60)
    movej(posj(0, 0, 0, 0, 0, POUR_ANGLE), mod=DR_MV_MOD_REL)

    return 1


# ═══════════════════════════════════════════════════
#  실행 (단독 테스트용 - 통합 시 이 블록만 팀 main()으로 이동)
# ═══════════════════════════════════════════════════
SCOOP_COUNT = 1

go_home()
pick_scoop()

i = 0
while i < SCOOP_COUNT:
    result = scoop_one_cycle(P_POUR)
    if result == 0:
        tp_log("!! 스쿠핑 실패 - 중단")
        break
    i = i + 1

return_scoop()
go_home()
tp_log("=== 스쿠핑 시퀀스 종료 ===")
```

---

### 3. 속도 튜닝 근거

| 구간 | 속도 | 근거 |
|---|---|---|
| 홈·스쿱 파지·이송 | 60% (선형) / 40% (관절) | 힘 감지 불필요, 충돌 리스크 낮음 |
| **PUSH 압착 구간** | **12mm/s (고정 저속 유지)** | 힘 감지 정확도가 속도에 민감. 빠르면 관성으로 임계값 오검출 |
| 후퇴~상승(BACK1→RISE) | 40mm/s | 힘 감지 불필요 구간, 이미 반력 해소된 상태 |
| 배출 회전 | 90% | 사용자 요청사항 — 컵 중앙에 정확히 떨어뜨리려면 빠른 회전 필요 |

**PUSH 구간은 절대 빠르게 하지 마세요.** 이 프로젝트에서 가장 많은 디버깅 시간이 들어간 부분이 이 구간의 힘 감지이며, 속도를 올리면 힘 추정값이 관성 영향을 받아 임계값 판정이 부정확해집니다.

---

### 4. 겪었던 문제와 원인 (팀원이 비슷한 작업 시 참고)

| 증상 | 원인 | 교훈 |
|---|---|---|
| 특정 자세에서 관절이 예상치 못하게 크게 돎 | ZYZ 오일러각 이중표현 — `(A,B,C)`와 `(A+180,-B,C+180)`가 물리적으로 동일 자세 | 인접 경유점끼리는 반드시 같은 "브랜치"로 좌표를 통일할 것 |
| 특정 위치+자세 조합에서 `NOT REACHABLE` | 낮은 높이에서 특정 자세(완전히 위를 보는 자세)는 물리적으로 도달 불가 | 저고도에서 극단적 자세를 요구하지 말고, 회전을 상승과 함께 진행할 것 |
| 힘 값이 항상 ±2N 노이즈만 나옴 | `task_compliance_ctrl` 없이 `get_tool_force()`만 호출하면 값이 갱신 안 됨 | 힘을 읽으려면 먼저 compliance 모드를 켜야 함 |
| 힘이 임계값을 넘겨도 로봇이 멈추지 않고 계속 밈 | `stx` 강성값을 반대로 설정 (밀리는 축을 고강성으로 둠) | **저항을 느껴야 하는 축은 반드시 저강성(300~500)**, 나머지는 고강성(3000) |
| DART 실행 자체가 안 됨 (문법 에러) | 주석에 특수문자(★, ─ 등) 포함 | 코드에는 순수 ASCII만 사용 |

---

### 5. 팀원 통합 시 반드시 확인할 것 (⚠️ 우선순위 높음)

#### 5-1. `P_POUR` 좌표 재검증 필수

현재 `P_POUR = posx(680.09, -238.02, 322.16, ...)`는 **제가 임의로 티칭한 배출 위치**입니다. 종이컵이 실제로 어디에 최종 안착하는지는 **컵 파지를 담당한 팀원의 좌표**에 달려 있습니다.

**해야 할 일:**
1. 팀원의 컵 배치 완료 좌표(예: `P_PL` 또는 `P_PLACE`) 확인
2. 그 컵 중심 바로 위 30~50mm 지점을 조그로 티칭
3. `P_POUR`를 그 값으로 교체

컵 위치와 배출 위치가 어긋나면 아이스크림이 컵 밖으로 떨어집니다.

#### 5-2. 좌표계·SOL 값 통일

이 스크립트는 전 구간 `SOL=2`로 검증됐습니다. 팀원 스크립트가 다른 `sol` 값을 쓴다면, **두 스크립트를 하나로 합칠 때 관절 구성이 충돌할 수 있습니다.** 통합 전에 서로의 `sol` 값을 맞춰보는 걸 권장합니다.

#### 5-3. 그리퍼 제어 함수 통일

이 스크립트는 컨트롤러 DO 1/2/3 (grasp / release / grasp_for_cup)을 사용합니다. 팀원도 동일한 함수를 쓰는지 확인하세요. 다르면 `grip_close()` / `grip_open()` 함수명이 충돌합니다 — 통합 시 하나로 통일하거나 접두어(`scoop_grip_close()` 등)를 붙이는 걸 권장합니다.

#### 5-4. 통합 순서 (제안)

```python
go_home()

# --- 팀원 담당 구간 ---
pick_cup()          # 종이컵 파지
flip_and_place_cup() # 뒤집어서 빨간컵 위 안착

# --- 제 담당 구간 ---
pick_scoop()
i = 0
while i < SCOOP_COUNT:
    result = scoop_one_cycle(P_POUR)   # ★ P_POUR = 팀원 컵 위치 기반으로 수정된 값
    if result == 0:
        break
    i = i + 1
return_scoop()

# --- 이후 미구현 구간 ---
# pick_spoon()
# insert_spoon()
# handover_cup()

go_home()
```

---

### 6. 아직 구현되지 않은 것 (다음 작업)

- [ ] **숟가락 취출·삽입** — 별도 매거진 좌표 티칭 필요
- [ ] **완성 컵 핸드오버** — 손님에게 제시, 파지 부하 감소로 수령 판정
- [ ] **표면 평탄화(LEVEL_SURFACE)** — 다중 스쿱 시 통 표면 정리 동작
- [ ] **`set_tool()` 실측 등록** — 현재 스쿱 무게중심 미등록 상태. 힘 감지 정확도에 직접 영향
- [ ] **잔량 소진 예외 처리** — `PROBE_SURFACE` 방식으로 표면 접촉 실패 시 처리
- [ ] **ROS2 노드 이관** — 현재 전부 DART DRL 스크립트. 최종적으로 `icecream_driver` 패키지의 `ExecuteMotion` 프리미티브로 이식 필요

---

### 7. 확정된 파라미터 (다른 팀원이 참고할 수치)

| 파라미터 | 값 | 비고 |
|---|---|---|
| 벽 압착 감지 임계값 | Fx ≤ -6.0N | 재료 저항 최대 관측치 -7.29N 기준 여유 확보 |
| 하드 안전 한계 | ±20N | 이 이상은 무조건 비상정지 |
| PUSH 압착 진입 깊이 | Z=125.00 (통 중앙 기준) | 통 Z 티칭값과 동일 |
| 벽 압착 최대 이동거리 | X 방향 +78.36mm (7스텝) | 필요시 스텝 추가 가능 |
| 배출 회전각 | 120도 | 180도에서 축소 (컵 안착 속도 문제로) |
| 안정화 대기 | 2.0초 (상승 후) / 1.5초 (배출 후) | 재료 낙하 완료 대기 |

---

### 8. 다음 작업 우선순위

1. **P_POUR 좌표 확정** (팀원 컵 위치 확인 즉시)
2. **`set_tool()` 스쿱 무게 등록** — 힘 감지 정확도의 기반
3. 통합 스크립트 1회 실기 테스트 (저속)
4. 숟가락 삽입 모션 추가
5. 핸드오버 모션 추가
6. 전체 시퀀스 3~5회 반복 테스트로 재현성 확인
