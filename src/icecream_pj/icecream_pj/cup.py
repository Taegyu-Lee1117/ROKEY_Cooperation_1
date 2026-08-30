"""DART 1~3단계: 홈 이동, 컵 파지, 뒤집기와 배치."""

from . import motion_config as c


class CupMotion:
    def __init__(self, robot):
        self.r = robot

    def go_home(self):
        self.r.movejx_cup(c.P_HOME, "P_HOME", c.VEL_J_SCOOP_SAFE, c.ACC_J_SCOOP_SAFE)
        self.r.wait(0.5)

    def pick(self):
        self.r.open_gripper()
        self.r.movejx_cup(c.P_CUP_APPROACH, "P_CUP_APPROACH", c.VEL_J_CUP_APPROACH, c.ACC_J_CUP_APPROACH)
        self.r.wait(0.3)
        self.r.movel(c.P_CUP_PICK, "P_CUP_PICK", c.VEL_X_CUP_SLOW, c.ACC_X_CUP_SLOW)
        self.r.wait(0.3)
        self.r.grip_with_retry(c.DO_CUP_GRIP, c.DI_CUP_GRIP, "CUP_PICK", "컵 파지")
        self.r.movel(c.P_CUP_LIFT, "P_CUP_LIFT", c.VEL_X_CUP_SLOW, c.ACC_X_CUP_SLOW)
        self.r.wait(0.3)
        self.r.movej([0, 0, 0, 0, 0, -180], "컵 뒤집기", c.CUP_FLIP_VELJ, c.CUP_FLIP_ACCJ, relative=True)
        self.r.wait(0.5)

    def place(self):
        self.r.movejx_cup(c.P_CUP_PLACE_APPROACH, "P_CUP_PLACE_APPROACH", c.VEL_J_CUP_CARRY, c.ACC_J_CUP_CARRY)
        self.r.wait(0.3)
        self.r.movel(c.P_CUP_PLACE_PRE, "P_CUP_PLACE_PRE", c.VEL_X_CUP_SLOW, c.ACC_X_CUP_SLOW)
        self.r.wait(0.2)
        self.r.movel(c.P_CUP_PLACE, "P_CUP_PLACE", c.VEL_X_CUP_PLACE, c.ACC_X_CUP_PLACE)
        self.r.wait(0.5)
        self.r.open_gripper()
        # 컵 배치 직후 낙하를 막기 위해 개방 완료를 기다린다.
        self.r.wait(1.0)
        self.r.movel(c.P_CUP_PLACE_PRE, "컵 배치 1차 이탈", c.VEL_X_CUP_PRE_RETREAT, c.ACC_X_CUP_PRE_RETREAT)
        self.r.movel(c.P_CUP_PLACE_RETREAT, "컵 배치 수직 이탈", c.VEL_X_CUP_SLOW, c.ACC_X_CUP_SLOW)
        self.r.wait(0.5)
        self.r.movel(c.P_CUP_EXIT_SAFE, "P_CUP_EXIT_SAFE", c.VEL_X_CUP_EXIT, c.ACC_X_CUP_EXIT)
        self.r.wait(0.5)
        self.r.movej([0, 0, 0, 0, 0, 180], "컵 뒤집기 J6 복귀", c.CUP_FLIP_VELJ, c.CUP_FLIP_ACCJ, relative=True)
        self.r.wait(0.5)

