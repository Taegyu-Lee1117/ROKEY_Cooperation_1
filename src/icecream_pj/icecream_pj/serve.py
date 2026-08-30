"""DART 11~12단계: 완성 컵 제공과 홈 복귀."""

from . import motion_config as c


class ServeMotion:
    def __init__(self, robot):
        self.r = robot

    def serve(self):
        self.r.movejx_cup(c.P_CUP_PLACE_APPROACH, "P_CUP_PLACE_APPROACH_SERVE", c.VEL_J_SERVE, c.ACC_J_SERVE)
        self.r.wait(0.5)
        self.r.movel(c.P_CUP_PLACE_PRE, "완성 컵 정렬", c.VEL_X_CUP_SLOW, c.ACC_X_CUP_SLOW)
        self.r.wait(0.3)
        self.r.movel(c.P_CUP_PLACE, "완성 컵 파지점", c.VEL_X_CUP_PLACE, c.ACC_X_CUP_PLACE)
        self.r.wait(0.5)
        self.r.grip_with_retry(c.DO_CUP_GRIP, c.DI_CUP_GRIP, "SERVE_CUP", "완성 컵 파지")
        self.r.movel(c.P_CUP_PLACE_PRE, "완성 컵 1차 상승", c.VEL_X_CUP_PRE_RETREAT, c.ACC_X_CUP_PRE_RETREAT)
        self.r.movel(c.P_CUP_PLACE_RETREAT, "완성 컵 상승", c.VEL_X_CUP_SLOW, c.ACC_X_CUP_SLOW)
        self.r.wait(0.5)
        self.r.movejx_cup(c.P_SERVE_APPROACH, "P_SERVE_APPROACH", c.VEL_J_SERVE, c.ACC_J_SERVE)
        self.r.wait(0.5)
        self.r.movel(c.P_SERVE_PLACE, "P_SERVE_PLACE", c.VEL_X_SERVE, c.ACC_X_SERVE)
        self.r.wait(0.5)
        self.r.open_gripper()
        if self.r.dr.get_digital_input(c.DI_CUP_GRIP) != 0:
            self.r.log("컵 제공 후 파지 확인 입력이 OFF가 아니지만 계속 진행합니다.")
        self.r.wait(1.0)
        self.r.movel(c.P_SERVE_APPROACH, "서빙 위치 이탈", c.VEL_X_SERVE, c.ACC_X_SERVE)
        self.r.wait(0.5)

    def return_home(self, home_j6):
        self.r.movejx_cup(c.P_HOME, "P_HOME_RETURN", c.VEL_J_SCOOP_SAFE, c.ACC_J_SCOOP_SAFE)
        self.r.wait(0.5)
        final = self.r._six(self.r.dr.get_current_posj())
        if final is None:
            raise RuntimeError("최종 관절 위치를 읽지 못했습니다.")
        delta = home_j6 - final[5]
        if abs(delta) > 0.5:
            self.r.movej([0, 0, 0, 0, 0, delta], "J6 최종 보정", c.CUP_FLIP_VELJ, c.CUP_FLIP_ACCJ, relative=True)
            self.r.wait(0.5)
