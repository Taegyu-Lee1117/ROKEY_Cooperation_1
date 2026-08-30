"""스쿱 파지, 힘 기반 스쿠핑, 컵 투입과 반환."""
import math

from . import motion_config as c


class ScoopMotion:
    def __init__(self, robot):
        self.r = robot

    def pick(self):
        self.r.open_gripper()
        self.r.movejx_scoop(c.P_SC_APP, "P_SC_APP", c.VEL_J_SCOOP_SAFE_FAST, c.ACC_J_SCOOP_SAFE_FAST)
        self.r.wait(0.5)
        # 파지점 15mm 위까지는 빠르게, 마지막 15mm만 정밀 속도로 접근
        self.r.movel(c.P_SC_PRE_GRIP, "P_SC_PRE_GRIP", c.VEL_X_SCOOP_PICK_RAPID, c.ACC_X_SCOOP_PICK_RAPID)
        self.r.movel(c.P_SC, "P_SC", c.VEL_X_SCOOP_PICK_FAST, c.ACC_X_SCOOP_PICK_FAST)
        self.r.wait(0.5)
        self.r.grip_with_retry(c.DO_SCOOP_GRIP, c.DI_SCOOP_GRIP, "SCOOP_PICK", "스쿱 파지")
        # 충돌 회피 경유점의 궤적을 보존하도록 작은 반경으로 블렌딩한다.
        self.r.movel(c.P_SC_UP, "P_SC_UP", c.VEL_X_SCOOP_PICK_FAST, c.ACC_X_SCOOP_PICK_FAST,
                     radius=c.SCOOP_TRANSFER_BLEND_RADIUS)

    def move_to_icecream(self, lane_dy):
        self.r.movej(c.J_SC_TRANSFER_SAFE, "J_SC_TRANSFER_SAFE", c.VEL_J_SCOOP_SAFE_FAST, c.ACC_J_SCOOP_SAFE_FAST,
                     radius=c.SCOOP_TRANSFER_BLEND_RADIUS)
        # 높은 안전점에서 진입 접근점까지 블렌딩한다.
        self.r.movejx_scoop(c.with_lane_dy(c.P_ICE_TRANSFER_HIGH, lane_dy), "P_ICE_TRANSFER_HIGH",
                             c.VEL_J_SCOOP_TRANSPORT_FAST, c.ACC_J_SCOOP_TRANSPORT_FAST,
                             radius=c.TRANSFER_BLEND_RADIUS)
        # 힘 기준값을 측정하기 전에 완전히 정지한다.
        self.r.movejx_scoop(c.with_lane_dy(c.P_EN_APP, lane_dy), "P_EN_APP",
                             c.VEL_J_SCOOP_SAFE_FAST, c.ACC_J_SCOOP_SAFE_FAST)
        self.r.wait(1.0)

    def _check_emergency_force(self, step_name):
        f = self.r.tool_force()
        self.r.log(f"{step_name} Fx={f[0]:.2f} Fy={f[1]:.2f} Fz={f[2]:.2f}")
        if any(abs(v) >= c.F_EMERGENCY_LIMIT for v in f[:3]):
            self.r.log(f"!!! 비상정지: 힘 한계(40N) 초과 [{step_name}] {f}")
            return True
        return False

    def _probe_ice_entry_z(self, lane_dy):
        """P_SCOOP_PRE_ENTRY ~ P_SCOOP_M1 사이를 1mm씩 내려가며 기준값 대비
        힘 변화량(X/Z 합성)이 F_ENTRY_DELTA를 연속 2회 넘으면 진입으로
        판단한다. 실패 시 None을 반환한다."""
        baseline = self.r.tool_force()
        baseline_fx, baseline_fz = baseline[0], baseline[2]
        self.r.log(f"ENTRY_BASELINE Fx={baseline_fx:.3f} Fz={baseline_fz:.3f}")

        entry = c.with_lane_dy(c.P_SCOOP_PRE_ENTRY, lane_dy)
        x, a, b, cc = entry[0], entry[3], entry[4], entry[5]
        y = entry[1]
        z = entry[2]
        z_limit = c.with_lane_dy(c.P_SCOOP_M1, lane_dy)[2]

        found_z = None
        hit = 0
        while z > z_limit:
            z = z - c.ENTRY_Z_STEP
            if z < z_limit:
                z = z_limit

            self.r.movel([x, y, z, a, b, cc], "ENTRY_PROBE", c.VEL_X_ICE_ENTRY_FAST, c.ACC_X_ICE_ENTRY_FAST)
            self.r.wait(c.ENTRY_Z_SETTLE_WAIT)

            f = self.r.tool_force()
            dx, dz = f[0] - baseline_fx, f[2] - baseline_fz
            delta = math.sqrt(dx * dx + dz * dz)
            self.r.log(f"ENTRY_PROBE z={z:.2f} Fx={f[0]:.2f} Fz={f[2]:.2f} delta={delta:.2f} hit={hit}")

            if delta >= c.F_ENTRY_HARD_LIMIT_DELTA:
                self.r.log("!! ENTRY_PROBE 델타 하드리밋 초과 - 중단")
                return None
            if self._check_emergency_force("ENTRY_PROBE"):
                return None

            if delta >= c.F_ENTRY_DELTA:
                hit += 1
            else:
                hit = 0
            if hit >= c.ENTRY_CONSEC_HIT_NEEDED:
                self.r.log(f"진입 감지: z={z:.2f} delta={delta:.2f}")
                return z

        if hit >= 1:
            self.r.wait(c.ENTRY_Z_SETTLE_WAIT)
            f = self.r.tool_force()
            dx, dz = f[0] - baseline_fx, f[2] - baseline_fz
            delta = math.sqrt(dx * dx + dz * dz)
            self.r.log(f"ENTRY_PROBE 경계 재확인 z={z:.2f} delta={delta:.2f}")
            if delta >= c.F_ENTRY_DELTA:
                self.r.log(f"진입 감지(경계 재확인): z={z:.2f} delta={delta:.2f}")
                return z

        self.r.log("!! 진입 힘 감지 실패 - 최대 깊이(P_SCOOP_M1)까지 델타 미도달")
        return None

    def scoop(self, lane_dy):
        self.r.movel(c.with_lane_dy(c.P_SCOOP_PRE_ENTRY, lane_dy), "P_SCOOP_PRE_ENTRY",
                     c.VEL_X_ICE_APPROACH_FAST, c.ACC_X_ICE_APPROACH_FAST)
        self.r.wait(0.5)

        found_z = self._probe_ice_entry_z(lane_dy)
        if found_z is None:
            raise RuntimeError("진입 힘 감지 실패로 스쿠핑을 중단했습니다.")

        self.r.movel(c.with_lane_dy(c.P_SCOOP_M2, lane_dy), "P_SCOOP_M2",
                     c.VEL_X_SCOOPING_FAST, c.ACC_X_SCOOPING_FAST, radius=c.SCOOP_BLEND_RADIUS)
        self.r.wait(0.05)
        if self._check_emergency_force("SCOOP_M2"):
            raise RuntimeError("비상정지: 힘 한계(40N) 초과 (SCOOP_M2)")

        self.r.movel(c.with_lane_dy(c.P_SCOOP_M3, lane_dy), "P_SCOOP_M3",
                     c.VEL_X_SCOOPING_FAST, c.ACC_X_SCOOPING_FAST, radius=c.SCOOP_BLEND_RADIUS)
        self.r.wait(0.05)
        if self._check_emergency_force("SCOOP_M3"):
            raise RuntimeError("비상정지: 힘 한계(40N) 초과 (SCOOP_M3)")

        self.r.movel(c.with_lane_dy(c.P_SCOOP_M4, lane_dy), "P_SCOOP_M4",
                     c.VEL_X_SCOOPING_FAST, c.ACC_X_SCOOPING_FAST)
        self.r.wait(0.2)
        if self._check_emergency_force("SCOOP_M4"):
            raise RuntimeError("비상정지: 힘 한계(40N) 초과 (SCOOP_M4)")

        self.r.movel(c.with_lane_dy(c.P_SCOOP_M5, lane_dy), "P_SCOOP_M5",
                     c.VEL_X_SCOOP_LIFT_FAST, c.ACC_X_SCOOP_LIFT_FAST)
        self.r.wait(0.25)
        if self._check_emergency_force("SCOOP_M5"):
            raise RuntimeError("비상정지: 힘 한계(40N) 초과 (SCOOP_M5)")

        self.r.movel(c.with_lane_dy(c.P_SCOOP_M6, lane_dy), "P_SCOOP_M6",
                     c.VEL_X_SCOOP_EXIT_FAST, c.ACC_X_SCOOP_EXIT_FAST)
        # 통 위에서 내용물이 안정될 때까지 기다린다.
        self.r.wait(1.0)
        if self._check_emergency_force("SCOOP_M6"):
            raise RuntimeError("비상정지: 힘 한계(40N) 초과 (SCOOP_M6)")

    def put_in_cup(self, lane_dy):
        """M6에서 컵까지 레인별 안전 경로로 이동한다.

        큰 자세 전환은 직선 보간 시 회전 방향이 모호하므로 첫 이동에
        관절 보간을 사용한다. 레인 2는 통 벽과 컵을 피해 Y축을 먼저 맞춘다.
        """
        m6_now = c.with_lane_dy(c.P_SCOOP_M6, lane_dy)
        pour = c.P_POUR

        if lane_dy == c.LANE_DY_LIST[0]:
            z_up = [m6_now[0], m6_now[1], pour[2], pour[3], pour[4], pour[5]]
            self.r.movejx_scoop(z_up, "PUT_IN_CUP_Z_UP", c.VEL_J_SCOOP_SAFE_FAST, c.ACC_J_SCOOP_SAFE_FAST)
            self.r.movel(pour, "P_POUR", c.VEL_X_FILLED_SCOOP_CARRY, c.ACC_X_FILLED_SCOOP_CARRY)
        else:
            z_and_y = [m6_now[0], pour[1], pour[2], pour[3], pour[4], pour[5]]
            self.r.movejx_scoop(z_and_y, "PUT_IN_CUP_Z_AND_Y", c.VEL_J_SCOOP_SAFE_FAST, c.ACC_J_SCOOP_SAFE_FAST)
            self.r.movel(pour, "P_POUR", c.VEL_X_FILLED_SCOOP_CARRY, c.ACC_X_FILLED_SCOOP_CARRY)

        self.r.wait(0.5)
        self.r.movej([0, 0, 0, 0, 0, -c.POUR_ANGLE], "아이스크림 배출", c.VEL_J_POUR, c.ACC_J_POUR, relative=True)
        self.r.wait(c.WAIT_DROP)
        self.r.movel([0, 0, 50, 0, 0, 0], "컵 위 Z축 이탈", c.VEL_X_POUR_RETREAT, c.ACC_X_POUR_RETREAT, relative=True)
        self.r.wait(0.5)
        self.r.movej([0, 0, 0, 0, 0, c.POUR_ANGLE], "배출 J6 복귀", c.VEL_J_POUR_RETURN, c.ACC_J_POUR_RETURN, relative=True)
        self.r.wait(0.5)

    def return_scoop(self):
        # 종이컵 적재 위치와의 충돌을 피한 뒤 스쿱 거치대로 이동한다.
        self.r.movel([0, 0, c.SCOOP_RETURN_LIFT_Z, 0, 0, 0], "SCOOP_RETURN_LIFT",
                     c.VEL_X_POUR_RETREAT, c.ACC_X_POUR_RETREAT, relative=True)
        self.r.wait(0.5)
        self.r.movejx_scoop(c.P_SC_APP, "P_SC_APP_RETURN", c.VEL_J_SCOOP_SAFE, c.ACC_J_SCOOP_SAFE)
        self.r.wait(0.5)
        self.r.movel(c.P_SC, "P_SC_RETURN", c.VEL_X_SCOOP_PICK, c.ACC_X_SCOOP_PICK)
        self.r.wait(0.5)
        self.r.open_gripper()
        self.r.movel(c.P_SC_APP, "P_SC_APP_RETREAT", c.VEL_X_SCOOP_PICK, c.ACC_X_SCOOP_PICK)
        self.r.wait(0.5)
