#!/usr/bin/env python3
"""로스킨라빈스 전체 자동화 ROS2 Python 노드.

대상 환경:
- Ubuntu 24.04 / ROS2 Jazzy
- Doosan Robotics M0609
- doosan-robot2 jazzy 브랜치
- OnRobot RG2 + WebLogic (DO1/DO2/DO3)

이 파일은 다음 두 방식으로 같은 코드를 실행할 수 있다.
1) ros2 run roskin_robot_full roskin_full
2) python3 roskin_full_node.py
"""

import math
import sys

import rclpy
import DR_init


ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"

DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL


class RoskinAutomation:
    """DART 최종 시퀀스를 Doosan ROS2 Python API로 실행한다."""

    def __init__(self, node, dr, posx, posj):
        self.node = node
        self.dr = dr
        self.posx = posx
        self.posj = posj
        self.compliance_active = False

        # 이동 속도 및 가속도
        self.VEL_X_NORMAL = [72.0, 36.0]
        self.ACC_X_NORMAL = [120.0, 60.0]
        self.VEL_X_SLOW = [27.0, 13.0]
        self.ACC_X_SLOW = [55.0, 27.0]
        self.VEL_J_NORMAL = 47.0
        self.ACC_J_NORMAL = 70.0
        self.VEL_J_SLOW = 31.0
        self.ACC_J_SLOW = 47.0
        self.VEL_J_CUP = 17.0
        self.ACC_J_CUP = 28.0

        # WebLogic 입력에 연결된 컨트롤박스 디지털 출력
        self.DO_SCOOP_GRIP = 1
        self.DO_GRIPPER_OPEN = 2
        self.DO_CUP_GRIP = 3

        # ROS2 MoveJointx가 허용하는 solution space는 0~7이다.
        # 컵 경로는 DART의 sol=255 동작을 아래 movejx_cup_auto()로 재현한다.
        self.SOL_SCOOP = 2

        # 컵 배치 미세 보정값
        self.CUP_CENTER_X_CORR = 0.0
        self.CUP_CENTER_Y_CORR = 0.0
        self.CUP_LEVEL_RX_CORR = 0.0
        self.CUP_LEVEL_RY_CORR = 0.0

        cup_x = 735.24 + self.CUP_CENTER_X_CORR
        cup_y = -197.38 + self.CUP_CENTER_Y_CORR
        cup_z = 230.31
        cup_rx = 163.37 + self.CUP_LEVEL_RX_CORR
        cup_ry = -99.32 + self.CUP_LEVEL_RY_CORR
        cup_rz = -89.19

        # 좌표
        self.P_HOME = posx([367.48, 3.07, 213.43, 89.68, 179.98, 90.19])

        self.P_CUP_APPROACH = posx(
            [736.66, -55.87, 295.85, 175.46, -102.53, 92.40]
        )
        self.P_CUP_PICK = posx(
            [736.66, -55.87, 225.85, 175.46, -102.53, 92.40]
        )
        self.P_CUP_LIFT = posx(
            [736.66, -55.87, 330.85, 175.46, -102.53, 92.40]
        )

        self.P_CUP_PLACE_APPROACH = posx(
            [cup_x, cup_y, 330.31, cup_rx, cup_ry, cup_rz]
        )
        self.P_CUP_PLACE_PRE = posx(
            [cup_x, cup_y, cup_z + 15.0, cup_rx, cup_ry, cup_rz]
        )
        self.P_CUP_PLACE = posx(
            [cup_x, cup_y, cup_z, cup_rx, cup_ry, cup_rz]
        )
        self.P_CUP_PLACE_RETREAT = posx(
            [cup_x, cup_y, 350.31, cup_rx, cup_ry, cup_rz]
        )

        self.P_CUP_EXIT_SAFE = posx(
            [620.00, -160.00, 350.00, 163.37, -99.32, -89.19]
        )
        self.P_SERVE_APPROACH = posx(
            [370.51, -454.53, 320.00, 163.37, -99.32, -89.19]
        )
        self.P_SERVE_PLACE = posx(
            [370.51, -454.53, 253.36, 163.37, -99.32, -89.19]
        )

        self.P_SC_APP = posx(
            [607.86, 115.34, 265.02, 62.45, 178.05, 63.29]
        )
        self.P_SC = posx(
            [607.86, 115.34, 145.02, 62.45, 178.05, 63.29]
        )
        self.P_SC_UP = posx(
            [607.86, 115.34, 245.02, 62.45, 178.05, 63.29]
        )

        self.P_EN_APP = posx(
            [366.75, -157.79, 275.00, 0.07, -143.31, 1.13]
        )
        self.P_EN = posx(
            [366.75, -157.79, 125.00, 0.07, -143.31, 1.13]
        )

        self.P_PUSH1 = posx(
            [397.30, -157.79, 125.00, -179.62, 173.74, -178.55]
        )
        self.P_PUSH2 = posx(
            [406.02, -157.79, 125.00, -0.96, 177.56, 0.11]
        )
        self.P_PUSH3 = posx(
            [414.75, -157.79, 125.00, -0.21, 168.87, 0.87]
        )
        self.P_PUSH4 = posx(
            [423.48, -157.79, 125.00, -0.12, 160.17, 0.96]
        )
        self.P_PUSH5 = posx(
            [432.20, -157.79, 125.00, -0.08, 151.48, 1.00]
        )
        self.P_PUSH6 = posx(
            [438.66, -157.79, 125.00, -0.06, 145.06, 1.02]
        )
        self.P_PUSH7 = posx(
            [445.11, -157.79, 125.00, -0.05, 138.65, 1.04]
        )

        self.P_BACK1 = posx(
            [387.64, -157.79, 230.00, -0.05, 133.00, 1.04]
        )
        self.P_RISE = posx(
            [346.75, -157.79, 318.34, -0.04, 108.00, 1.06]
        )
        self.P_POUR = posx(
            [680.09, -238.02, 322.16, 0.42, 104.43, 1.08]
        )

        self.WAIT_SETTLE = 2.0
        self.WAIT_WALL = 0.7
        self.WAIT_DROP = 1.5

        self.F_WALL_TARGET = -6.0
        self.F_WALL_TARGET_ABS = 6.0
        self.F_HARD_LIMIT = 20.0
        self.F_BOTTOM_TARGET = 9.0
        self.POUR_ANGLE = 120.0

        self.SPEED_PUSH = 13.0
        self.SPEED_PUSH_ACC = 9.0
        self.SPEED_RETREAT = 44.0
        self.SPEED_TRANSPORT_L = 94.0
        self.SPEED_TRANSPORT_J = 62.0
        self.SPEED_POUR_APPROACH = 66.0
        self.SPEED_POUR_APPROACH_ACC = 44.0

        self.CUP_FLIP_VELJ = 29.0
        self.CUP_FLIP_ACCJ = 57.0
        self.PUSH_BLEND_R = 1.5
        self.SCOOP_COUNT = 2

    def log(self, message):
        self.node.get_logger().info(str(message))

    def warn(self, message):
        self.node.get_logger().warning(str(message))

    @staticmethod
    def _as_finite_six(values):
        try:
            result = [float(value) for value in values]
        except (TypeError, ValueError):
            return None
        if len(result) != 6 or not all(math.isfinite(value) for value in result):
            return None
        return result

    def _candidate_matches_target(self, candidate, target):
        """IK 서비스 실패로 반환될 수 있는 무효 관절값을 FK로 걸러낸다."""
        try:
            fk_pose = self._as_finite_six(
                self.dr.fkin(candidate, ref=self.dr.DR_BASE)
            )
            target_pose = self._as_finite_six(target)
        except Exception:
            return False
        if fk_pose is None or target_pose is None:
            return False

        xyz_error = math.sqrt(
            sum((fk_pose[index] - target_pose[index]) ** 2 for index in range(3))
        )
        return xyz_error <= 2.0

    def select_nearest_solution(self, target, point_name):
        """DART sol=255와 같은 기준으로 ROS2용 0~7 해를 선택한다.

        현재 관절값에 대해 J2~J5의 L2 거리가 가장 작은 유효 IK 해를 고른다.
        """
        current = self._as_finite_six(self.dr.get_current_posj())
        if current is None:
            raise RuntimeError("현재 관절 위치를 읽지 못했습니다.")

        best_solution = None
        best_score = None

        for solution in range(8):
            try:
                candidate = self._as_finite_six(
                    self.dr.ikin(target, solution, ref=self.dr.DR_BASE)
                )
            except Exception as error:
                self.warn(
                    f"{point_name}: solution {solution} IK 확인 실패: {error!r}"
                )
                continue

            if candidate is None or not self._candidate_matches_target(candidate, target):
                continue

            score = sum(
                (candidate[index] - current[index]) ** 2
                for index in range(1, 5)
            )
            if best_score is None or score < best_score:
                best_score = score
                best_solution = solution

        if best_solution is None:
            raise RuntimeError(
                f"{point_name}: 사용할 수 있는 solution space(0~7)가 없습니다."
            )

        self.log(f"{point_name}: 자동 선택 solution={best_solution}")
        return best_solution

    def movejx_cup_auto(self, target, point_name, vel=None, acc=None):
        solution = self.select_nearest_solution(target, point_name)
        kwargs = {
            "ref": self.dr.DR_BASE,
            "sol": solution,
        }
        if vel is not None:
            kwargs["vel"] = vel
        if acc is not None:
            kwargs["acc"] = acc
        result = self.dr.movejx(target, **kwargs)
        if result != 0:
            raise RuntimeError(f"{point_name}: movejx 실패, 반환값={result}")

    def movejx_scoop(self, target, point_name, vel=None, acc=None):
        kwargs = {
            "ref": self.dr.DR_BASE,
            "sol": self.SOL_SCOOP,
        }
        if vel is not None:
            kwargs["vel"] = vel
        if acc is not None:
            kwargs["acc"] = acc
        result = self.dr.movejx(target, **kwargs)
        if result != 0:
            raise RuntimeError(
                f"{point_name}: movejx 실패(SOL={self.SOL_SCOOP}), 반환값={result}"
            )

    def init_outputs(self):
        self.dr.set_digital_output(self.DO_SCOOP_GRIP, 0)
        self.dr.set_digital_output(self.DO_GRIPPER_OPEN, 0)
        self.dr.set_digital_output(self.DO_CUP_GRIP, 0)
        self.dr.wait(0.5)

    def grip_open_all(self):
        self.dr.set_digital_output(self.DO_SCOOP_GRIP, 0)
        self.dr.set_digital_output(self.DO_CUP_GRIP, 0)
        self.dr.set_digital_output(self.DO_GRIPPER_OPEN, 1)
        self.dr.wait(1.5)

    def grip_scoop_close(self):
        self.dr.set_digital_output(self.DO_GRIPPER_OPEN, 0)
        self.dr.wait(0.3)
        self.dr.set_digital_output(self.DO_SCOOP_GRIP, 1)
        self.dr.wait(1.5)

    def force_base(self):
        return self._as_finite_six(
            self.dr.get_tool_force(ref=self.dr.DR_BASE)
        )

    def release_force_control(self):
        try:
            self.dr.release_force()
            self.dr.wait(0.2)
        finally:
            try:
                self.dr.release_compliance_ctrl()
                self.dr.wait(0.2)
            finally:
                self.compliance_active = False

    def emergency_check(self, force):
        if force is None:
            self.warn("!! 비상: 툴 힘 값을 읽지 못했습니다.")
            if self.compliance_active:
                self.release_force_control()
            return 1

        if (
            force[0] <= -self.F_HARD_LIMIT
            or force[2] <= -self.F_HARD_LIMIT
            or force[2] >= self.F_HARD_LIMIT
        ):
            self.warn("!! 비상: 힘 한계(20N) 초과 " + str(force))
            if self.compliance_active:
                self.release_force_control()
            return 1
        return 0

    def check_wall(self, step_label):
        force = self.force_base()
        if force is None:
            self.warn(step_label + " : 툴 힘 읽기 실패")
            return 2

        self.log(
            f"{step_label} Fx={force[0]} Fy={force[1]} Fz={force[2]}"
        )

        if self.emergency_check(force) == 1:
            return 2

        if abs(force[2]) >= self.F_BOTTOM_TARGET:
            self.warn(step_label + " : 통 바닥 감지 - 잔량 소진")
            return 3

        if force[0] <= self.F_WALL_TARGET:
            self.log(step_label + " : Fx 조건으로 정지")
            return 1
        if abs(force[1]) >= self.F_WALL_TARGET_ABS:
            self.log(step_label + " : Fy 조건으로 정지")
            return 1
        if abs(force[2]) >= self.F_WALL_TARGET_ABS:
            self.log(step_label + " : Fz 조건으로 정지")
            return 1
        return 0

    def go_home(self):
        self.movejx_cup_auto(
            self.P_HOME,
            "P_HOME",
            vel=self.VEL_J_SLOW,
            acc=self.ACC_J_SLOW,
        )
        self.dr.wait(0.5)

    def pick_and_place_cup(self):
        self.log("컵 파지 및 배치 시작")
        self.grip_open_all()

        self.movejx_cup_auto(
            self.P_CUP_APPROACH,
            "P_CUP_APPROACH",
            vel=self.VEL_J_NORMAL,
            acc=self.ACC_J_NORMAL,
        )
        self.dr.wait(0.3)

        self.dr.movel(
            self.P_CUP_PICK,
            vel=self.VEL_X_SLOW,
            acc=self.ACC_X_SLOW,
            ref=self.dr.DR_BASE,
        )
        self.dr.wait(0.3)

        self.dr.set_digital_output(self.DO_GRIPPER_OPEN, 0)
        self.dr.wait(0.3)
        self.dr.set_digital_output(self.DO_CUP_GRIP, 1)
        self.dr.wait(1.5)

        self.dr.movel(
            self.P_CUP_LIFT,
            vel=self.VEL_X_SLOW,
            acc=self.ACC_X_SLOW,
            ref=self.dr.DR_BASE,
        )

        # J6 -180도 단일 명령: 중간 -90도 정지 없이 한 번에 뒤집기
        self.dr.set_velj(self.CUP_FLIP_VELJ)
        self.dr.set_accj(self.CUP_FLIP_ACCJ)
        self.dr.movej(
            self.posj([0.0, 0.0, 0.0, 0.0, 0.0, -180.0]),
            mod=self.dr.DR_MV_MOD_REL,
        )
        self.dr.wait(0.5)

        self.movejx_cup_auto(
            self.P_CUP_PLACE_APPROACH,
            "P_CUP_PLACE_APPROACH",
            vel=self.VEL_J_CUP,
            acc=self.ACC_J_CUP,
        )
        self.dr.wait(0.3)

        self.dr.movel(
            self.P_CUP_PLACE_PRE,
            vel=self.VEL_X_SLOW,
            acc=self.ACC_X_SLOW,
            ref=self.dr.DR_BASE,
        )
        self.dr.wait(0.2)

        self.dr.movel(
            self.P_CUP_PLACE,
            vel=[8.0, 4.0],
            acc=[16.0, 8.0],
            ref=self.dr.DR_BASE,
        )
        self.dr.wait(0.8)

        self.dr.set_digital_output(self.DO_CUP_GRIP, 0)
        self.dr.wait(0.5)
        self.dr.set_digital_output(self.DO_GRIPPER_OPEN, 1)
        self.dr.wait(3.0)

        self.dr.movel(
            self.P_CUP_PLACE_PRE,
            vel=[10.0, 5.0],
            acc=[20.0, 10.0],
            ref=self.dr.DR_BASE,
        )
        self.dr.movel(
            self.P_CUP_PLACE_RETREAT,
            vel=self.VEL_X_SLOW,
            acc=self.ACC_X_SLOW,
            ref=self.dr.DR_BASE,
        )
        self.dr.wait(0.5)

        self.dr.movel(
            self.P_CUP_EXIT_SAFE,
            vel=[42.0, 18.0],
            acc=[72.0, 36.0],
            ref=self.dr.DR_BASE,
        )
        self.dr.wait(0.5)

    def unwind_and_pick_scoop(self):
        self.log("스쿱 파지 시작")
        self.dr.set_velj(self.CUP_FLIP_VELJ)
        self.dr.set_accj(self.CUP_FLIP_ACCJ)
        self.dr.movej(
            self.posj([0.0, 0.0, 0.0, 0.0, 0.0, 180.0]),
            mod=self.dr.DR_MV_MOD_REL,
        )
        self.dr.wait(0.3)

        self.dr.set_velx(self.SPEED_TRANSPORT_L, self.SPEED_TRANSPORT_J)
        self.dr.set_accx(100.0, 60.0)
        self.grip_open_all()

        self.movejx_scoop(self.P_SC_APP, "P_SC_APP_PICK")

        self.dr.set_velx(27.0, 17.0)
        self.dr.movel(self.P_SC)

        self.grip_scoop_close()
        if self.dr.get_digital_input(1) == 0:
            self.warn("!! 스쿱 파지 확인 신호 없음")

        self.dr.movel(self.P_SC_UP)
        self.dr.wait(0.3)

    def return_scoop(self):
        self.log("스쿱 반환 시작")
        self.dr.set_velx(self.SPEED_TRANSPORT_L, self.SPEED_TRANSPORT_J)
        self.movejx_scoop(self.P_SC_APP, "P_SC_APP_RETURN")
        self.dr.set_velx(27.0, 17.0)
        self.dr.movel(self.P_SC)
        self.grip_open_all()
        self.dr.movel(self.P_SC_APP)

    def scoop_one_cycle(self, pour_target):
        self.dr.set_velx(self.SPEED_TRANSPORT_L, self.SPEED_TRANSPORT_J)
        self.movejx_scoop(self.P_EN_APP, "P_EN_APP")

        self.dr.set_velx(27.0, 17.0)
        self.dr.movel(self.P_EN)
        self.dr.wait(0.2)

        self.dr.task_compliance_ctrl(
            stx=[400.0, 3000.0, 3000.0, 3000.0, 3000.0, 3000.0]
        )
        self.compliance_active = True
        # ROS2 서비스의 모드 전환 완료 시간을 확보한다.
        self.dr.wait(0.5)
        self.dr.set_desired_force(
            fd=[3.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            dir=[1, 0, 0, 0, 0, 0],
            mod=self.dr.DR_FC_MOD_REL,
        )
        self.dr.wait(0.2)

        self.dr.set_velx(self.SPEED_PUSH, self.SPEED_PUSH_ACC)
        self.dr.movel(self.P_PUSH1, radius=self.PUSH_BLEND_R)
        self.dr.wait(0.15)
        if self.emergency_check(self.force_base()) == 1:
            return 0

        push_points = [
            self.P_PUSH2,
            self.P_PUSH3,
            self.P_PUSH4,
            self.P_PUSH5,
            self.P_PUSH6,
            self.P_PUSH7,
        ]

        for index, point in enumerate(push_points):
            if index == len(push_points) - 1:
                self.dr.movel(point)
            else:
                self.dr.movel(point, radius=self.PUSH_BLEND_R)

            self.dr.wait(0.12)
            result = self.check_wall("PUSH_STEP" + str(index + 2))
            if result == 2:
                return 0
            if result == 3:
                if self.compliance_active:
                    self.release_force_control()
                return -1
            if result == 1:
                break

        if self.compliance_active:
            self.release_force_control()

        self.dr.wait(self.WAIT_WALL)

        self.dr.set_velx(self.SPEED_RETREAT, 25.0)
        self.dr.movel(self.P_BACK1)
        self.dr.set_velx(self.SPEED_RETREAT, 25.0)
        self.dr.movel(self.P_RISE)

        self.dr.wait(self.WAIT_SETTLE)

        self.dr.set_velx(
            self.SPEED_POUR_APPROACH,
            self.SPEED_POUR_APPROACH_ACC,
        )
        self.dr.movel(pour_target)
        self.dr.wait(0.3)

        self.dr.set_velj(90.0)
        self.dr.set_accj(120.0)
        self.dr.movej(
            self.posj([0.0, 0.0, 0.0, 0.0, 0.0, -self.POUR_ANGLE]),
            mod=self.dr.DR_MV_MOD_REL,
        )
        self.dr.wait(self.WAIT_DROP)

        self.dr.set_velj(30.0)
        self.dr.set_accj(60.0)
        self.dr.movej(
            self.posj([0.0, 0.0, 0.0, 0.0, 0.0, self.POUR_ANGLE]),
            mod=self.dr.DR_MV_MOD_REL,
        )
        return 1

    def serve_cup(self):
        self.log("완성 컵 제공 시작")
        self.movejx_cup_auto(
            self.P_CUP_PLACE_APPROACH,
            "P_CUP_PLACE_APPROACH_SERVE",
            vel=self.VEL_J_CUP,
            acc=self.ACC_J_CUP,
        )
        self.dr.wait(0.3)

        self.dr.movel(
            self.P_CUP_PLACE,
            vel=self.VEL_X_SLOW,
            acc=self.ACC_X_SLOW,
            ref=self.dr.DR_BASE,
        )
        self.dr.wait(0.3)

        self.dr.set_digital_output(self.DO_GRIPPER_OPEN, 0)
        self.dr.wait(0.3)
        self.dr.set_digital_output(self.DO_CUP_GRIP, 1)
        self.dr.wait(1.5)

        if self.dr.get_digital_input(3) == 0:
            self.warn("!! 완성 컵 파지 확인 신호 없음")

        self.dr.movel(
            self.P_CUP_PLACE_RETREAT,
            vel=self.VEL_X_SLOW,
            acc=self.ACC_X_SLOW,
            ref=self.dr.DR_BASE,
        )
        self.dr.wait(0.5)

        self.movejx_cup_auto(
            self.P_SERVE_APPROACH,
            "P_SERVE_APPROACH",
            vel=self.VEL_J_NORMAL,
            acc=self.ACC_J_NORMAL,
        )
        self.dr.wait(0.3)

        self.dr.movel(
            self.P_SERVE_PLACE,
            vel=self.VEL_X_SLOW,
            acc=self.ACC_X_SLOW,
            ref=self.dr.DR_BASE,
        )
        self.dr.wait(0.5)

        self.dr.set_digital_output(self.DO_CUP_GRIP, 0)
        self.dr.wait(0.5)
        self.dr.set_digital_output(self.DO_GRIPPER_OPEN, 1)
        self.dr.wait(1.5)

        self.dr.movel(
            self.P_SERVE_APPROACH,
            vel=self.VEL_X_SLOW,
            acc=self.ACC_X_SLOW,
            ref=self.dr.DR_BASE,
        )
        self.dr.wait(0.3)

    def run(self):
        self.log("3초 후 로스킨라빈스 통합 시퀀스를 시작합니다.")
        self.dr.wait(3.0)

        self.dr.set_ref_coord(self.dr.DR_BASE)
        self.dr.set_tcp("GripperDA_v1_A3")
        self.init_outputs()

        self.go_home()
        home_posj = self._as_finite_six(self.dr.get_current_posj())
        if home_posj is None:
            raise RuntimeError("홈 위치 관절값을 읽지 못했습니다.")
        home_j6 = home_posj[5]

        self.pick_and_place_cup()
        self.unwind_and_pick_scoop()

        completed_count = 0
        while completed_count < self.SCOOP_COUNT:
            self.log(
                f"스쿠핑 {completed_count + 1}/{self.SCOOP_COUNT} 시작"
            )
            result = self.scoop_one_cycle(self.P_POUR)
            if result == -1:
                self.warn("!! 잔량 소진 - 중단")
                break
            if result == 0:
                self.warn("!! 스쿠핑 실패 - 중단")
                break
            completed_count += 1

        self.return_scoop()
        self.serve_cup()
        self.go_home()

        final_posj = self._as_finite_six(self.dr.get_current_posj())
        if final_posj is None:
            raise RuntimeError("최종 관절값을 읽지 못했습니다.")

        delta_j6 = home_j6 - final_posj[5]
        if abs(delta_j6) > 0.5:
            self.log(f"J6 보정: {delta_j6}도")
            self.dr.set_velj(self.CUP_FLIP_VELJ)
            self.dr.set_accj(self.CUP_FLIP_ACCJ)
            self.dr.movej(
                self.posj([0.0, 0.0, 0.0, 0.0, 0.0, delta_j6]),
                mod=self.dr.DR_MV_MOD_REL,
            )
            self.dr.wait(0.3)

        self.log("=== 통합 시퀀스 종료 ===")

    def stop_force_control_safely(self):
        if self.compliance_active:
            try:
                self.release_force_control()
            except Exception as error:
                self.warn("힘/순응제어 해제 실패: " + repr(error))


def main(args=None):
    rclpy.init(args=args)
    node = rclpy.create_node("roskin_full", namespace=ROBOT_ID)
    DR_init.__dsr__node = node

    program = None
    try:
        # DR_init의 로봇 ID/model/node 설정 후 import해야 한다.
        import DSR_ROBOT2 as dr
        from DR_common2 import posj, posx

        program = RoskinAutomation(node, dr, posx, posj)
        program.run()

    except KeyboardInterrupt:
        node.get_logger().warning("사용자가 실행을 중단했습니다.")
    except Exception as error:
        node.get_logger().error("작업 중 오류 발생: " + repr(error))
        node.get_logger().warning(
            "물체 낙하 방지를 위해 그리퍼 출력은 자동 해제하지 않습니다."
        )
    finally:
        if program is not None:
            program.stop_force_control_safely()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
