"""Doosan 공통 이동, I/O 및 모션 오류 처리."""

import math

from . import motion_config as cfg


class MotionError(RuntimeError):
    def __init__(self, process_step, error_code, message):
        super().__init__(message)
        self.process_step = process_step
        self.error_code = error_code
        self.message = message


class RobotController:
    def __init__(self, node, dr, posx, posj):
        self.node = node
        self.dr = dr
        self.posx = posx
        self.posj = posj

    def x(self, values):
        return self.posx(values)

    def j(self, values):
        return self.posj(values)

    def log(self, message):
        self.node.get_logger().info(str(message))

    def _check(self, result, label):
        if result not in (None, 0):
            raise RuntimeError(f"{label} 실패, 반환값={result}")

    @staticmethod
    def _six(values):
        try:
            result = [float(value) for value in values]
        except (TypeError, ValueError):
            return None
        return result if len(result) == 6 and all(map(math.isfinite, result)) else None

    def select_nearest_solution(self, target, label):
        """DART sol=255 대신 현재 자세와 가장 가까운 유효한 0~7 해를 고른다."""
        current = self._six(self.dr.get_current_posj())
        if current is None:
            raise RuntimeError("현재 관절 위치를 읽지 못했습니다.")
        best = None
        for solution in range(8):
            try:
                candidate = self._six(self.dr.ikin(target, solution, ref=self.dr.DR_BASE))
                if candidate is None:
                    continue
                fk = self._six(self.dr.fkin(candidate, ref=self.dr.DR_BASE))
                wanted = self._six(target)
                if fk is None or wanted is None:
                    continue
                xyz_error = sum((fk[i] - wanted[i]) ** 2 for i in range(3)) ** 0.5
                if xyz_error > 2.0:
                    continue
                score = sum((candidate[i] - current[i]) ** 2 for i in range(6))
                if best is None or score < best[0]:
                    best = (score, solution)
            except Exception as error:
                self.node.get_logger().warning(f"{label}: solution {solution} 제외: {error}")
        if best is None:
            raise RuntimeError(f"{label}: 유효한 solution(0~7)이 없습니다.")
        self.log(f"{label}: solution={best[1]} 자동 선택")
        return best[1]

    def movejx_cup(self, values, label, vel, acc, radius=None):
        target = self.x(values)
        kwargs = {"vel": vel, "acc": acc, "sol": cfg.SOL_CUP, "ref": self.dr.DR_BASE}
        if radius is not None:
            kwargs["radius"] = radius
        self._check(self.dr.movejx(target, **kwargs), label)

    def movejx_scoop(self, values, label, vel, acc, radius=None):
        target = self.x(values)
        kwargs = {"vel": vel, "acc": acc, "sol": cfg.SOL_SCOOP, "ref": self.dr.DR_BASE}
        if radius is not None:
            kwargs["radius"] = radius
        self._check(self.dr.movejx(target, **kwargs), label)

    def movej(self, values, label, vel, acc, relative=False, radius=None):
        kwargs = {"vel": vel, "acc": acc}
        if relative:
            kwargs["mod"] = self.dr.DR_MV_MOD_REL
        if radius is not None:
            kwargs["radius"] = radius
        self._check(self.dr.movej(self.j(values), **kwargs), label)

    def movel(self, values, label, vel, acc, relative=False, radius=None):
        kwargs = {"vel": vel, "acc": acc, "ref": self.dr.DR_BASE}
        if relative:
            kwargs["mod"] = self.dr.DR_MV_MOD_REL
        if radius is not None:
            kwargs["radius"] = radius
        self._check(self.dr.movel(self.x(values), **kwargs), label)

    def wait(self, seconds):
        self.dr.wait(seconds)

    def tool_force(self):
        return self.dr.get_tool_force(ref=self.dr.DR_BASE)

    def init_robot(self):
        self.dr.set_ref_coord(self.dr.DR_BASE)
        self.dr.set_tcp(cfg.TCP_NAME)
        self.dr.set_digital_output(cfg.DO_SCOOP_GRIP, 0)
        self.dr.set_digital_output(cfg.DO_GRIPPER_OPEN, 0)
        self.dr.set_digital_output(cfg.DO_CUP_GRIP, 0)
        self.wait(0.5)

    def prepare_manual_motion(self):
        """관리자 수동 명령 전에 기준 좌표계와 TCP만 준비한다."""
        self.dr.set_ref_coord(self.dr.DR_BASE)
        self.dr.set_tcp(cfg.TCP_NAME)

    def open_gripper(self):
        self.dr.set_digital_output(cfg.DO_SCOOP_GRIP, 0)
        self.dr.set_digital_output(cfg.DO_CUP_GRIP, 0)
        self.dr.set_digital_output(cfg.DO_GRIPPER_OPEN, 1)
        # 공압 액추에이터가 개방을 마칠 시간을 확보한다.
        self.wait(1.0)

    def _grip_once(self, output, input_number):
        self.dr.set_digital_output(cfg.DO_GRIPPER_OPEN, 0)
        self.dr.set_digital_output(cfg.DO_SCOOP_GRIP, 0)
        self.dr.set_digital_output(cfg.DO_CUP_GRIP, 0)
        self.wait(0.3)
        self.dr.set_digital_output(output, 1)
        # 공압 액추에이터가 파지를 마칠 시간을 확보한다.
        self.wait(1.0)
        self.wait(0.3)
        if self.dr.get_digital_input(input_number) == 1:
            return True
        self.wait(0.2)
        return self.dr.get_digital_input(input_number) == 1

    def grip_with_retry(self, output, input_number, step, label):
        if not self._grip_once(output, input_number):
            self.log(f"{label} 확인 입력이 없지만 원본 동작대로 계속 진행합니다.")

    def grip_cup(self):
        self.grip_with_retry(cfg.DO_CUP_GRIP, cfg.DI_CUP_GRIP, "ADMIN", "컵 파지")

    def grip_scoop(self):
        self.grip_with_retry(cfg.DO_SCOOP_GRIP, cfg.DI_SCOOP_GRIP, "ADMIN", "스쿱 파지")

    def soft_stop(self):
        self.dr.stop(self.dr.DR_SSTOP)
