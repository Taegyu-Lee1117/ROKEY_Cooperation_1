#!/usr/bin/env python3

import sys

import rclpy
import DR_init


ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"

DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL


def main(args=None):
    rclpy.init(args=args)
    node = rclpy.create_node("roskin_icecream_1to5", namespace=ROBOT_ID)
    DR_init.__dsr__node = node

    try:
        from DSR_ROBOT2 import (
            DR_BASE,
            movejx,
            movel,
            set_digital_output,
            set_ref_coord,
            wait,
        )
        from DR_common2 import posx
    except ImportError as error:
        node.get_logger().error(
            "DSR_ROBOT2를 불러오지 못했습니다: " + str(error)
        )
        node.get_logger().error(
            "doosan-robot2 빌드와 source ~/ros2_ws/install/setup.bash를 확인하세요."
        )
        node.destroy_node()
        rclpy.shutdown()
        return

    ON = 1
    OFF = 0

    # 이동 속도/가속도
    VEL_X_SLOW = [25.0, 12.0]
    ACC_X_SLOW = [50.0, 25.0]

    VEL_J_NORMAL = 30.0
    ACC_J_NORMAL = 45.0

    VEL_J_SLOW = 20.0
    ACC_J_SLOW = 30.0

    VEL_J_CUP = 15.0
    ACC_J_CUP = 25.0

    # WebLogic 입력과 연결된 컨트롤박스 디지털 출력
    DO_SCOOP_GRIP = 1
    DO_GRIPPER_OPEN = 2
    DO_CUP_GRIP = 3

    # 좌표: posx([X, Y, Z, Rx, Ry, Rz])
    P_HOME = posx([
        367.48, 3.07, 213.43,
        89.68, 179.98, 90.19,
    ])

    P_CUP_APPROACH = posx([
        736.66, -55.87, 295.85,
        175.46, -102.53, 92.40,
    ])

    P_CUP_PICK = posx([
        736.66, -55.87, 225.85,
        175.46, -102.53, 92.40,
    ])

    P_CUP_LIFT = posx([
        736.66, -55.87, 330.85,
        175.46, -102.53, 92.40,
    ])

    P_CUP_ROTATE_MID = posx([
        736.66, -55.87, 330.85,
        175.46, -102.53, 2.40,
    ])

    P_CUP_FLIP_END = posx([
        736.66, -55.87, 330.85,
        175.46, -102.53, -87.60,
    ])

    P_CUP_PLACE_APPROACH = posx([
        738.24, -200.38, 330.31,
        163.37, -99.32, -89.19,
    ])

    P_CUP_PLACE = posx([
        738.24, -200.38, 230.31,
        163.37, -99.32, -89.19,
    ])

    P_CUP_PLACE_RETREAT = posx([
        738.24, -200.38, 350.31,
        163.37, -99.32, -89.19,
    ])

    P_CUP_EXIT_SAFE = posx([
        620.00, -160.00, 350.00,
        163.37, -99.32, -89.19,
    ])

    P_SCOOP_READY = posx([
        607.86, 115.34, 213.43,
        62.45, 178.05, 63.29,
    ])

    P_SCOOP_PICK = posx([
        607.86, 115.34, 145.02,
        62.45, 178.05, 63.29,
    ])

    P_SCOOP_LIFT = posx([
        607.86, 115.34, 213.43,
        62.45, 178.05, 63.29,
    ])

    P_ICE_READY = posx([
        366.75, -157.79, 212.38,
        97.10, -179.96, 98.18,
    ])

    try:
        node.get_logger().info("3초 후 1~5단계 작업을 시작합니다.")
        wait(3.0)
        set_ref_coord(DR_BASE)

        # 모든 WebLogic 입력 초기화
        set_digital_output(DO_SCOOP_GRIP, OFF)
        set_digital_output(DO_GRIPPER_OPEN, OFF)
        set_digital_output(DO_CUP_GRIP, OFF)
        wait(0.5)

        # 홈
        movejx(P_HOME, vel=VEL_J_SLOW, acc=ACC_J_SLOW, sol=255)
        wait(0.8)

        # 3단계: 컵 파지
        set_digital_output(DO_SCOOP_GRIP, OFF)
        set_digital_output(DO_CUP_GRIP, OFF)
        set_digital_output(DO_GRIPPER_OPEN, ON)
        wait(1.5)

        movejx(P_CUP_APPROACH, vel=VEL_J_NORMAL, acc=ACC_J_NORMAL, sol=255)
        wait(0.3)

        movel(P_CUP_PICK, vel=VEL_X_SLOW, acc=ACC_X_SLOW, ref=DR_BASE)
        wait(0.3)

        set_digital_output(DO_GRIPPER_OPEN, OFF)
        wait(0.3)
        set_digital_output(DO_CUP_GRIP, ON)
        wait(1.5)

        movel(P_CUP_LIFT, vel=VEL_X_SLOW, acc=ACC_X_SLOW, ref=DR_BASE)
        wait(0.5)

        # 컵 제자리 회전
        movel(
            P_CUP_ROTATE_MID,
            vel=[20.0, 12.0],
            acc=[40.0, 20.0],
            ref=DR_BASE,
        )
        wait(0.3)

        movel(
            P_CUP_FLIP_END,
            vel=[20.0, 12.0],
            acc=[40.0, 20.0],
            ref=DR_BASE,
        )
        wait(0.8)

        # 4단계: 컵 배치
        movejx(
            P_CUP_PLACE_APPROACH,
            vel=VEL_J_CUP,
            acc=ACC_J_CUP,
            sol=255,
        )
        wait(0.5)

        movel(P_CUP_PLACE, vel=VEL_X_SLOW, acc=ACC_X_SLOW, ref=DR_BASE)
        wait(0.5)

        set_digital_output(DO_CUP_GRIP, OFF)
        wait(0.5)
        set_digital_output(DO_GRIPPER_OPEN, ON)
        wait(2.5)

        movel(
            P_CUP_PLACE_RETREAT,
            vel=VEL_X_SLOW,
            acc=ACC_X_SLOW,
            ref=DR_BASE,
        )
        wait(0.5)

        movel(
            P_CUP_EXIT_SAFE,
            vel=[35.0, 15.0],
            acc=[60.0, 30.0],
            ref=DR_BASE,
        )
        wait(0.5)

        movejx(P_HOME, vel=VEL_J_SLOW, acc=ACC_J_SLOW, sol=255)
        wait(0.8)

        # 5단계: 스쿱 파지
        movejx(P_SCOOP_READY, vel=VEL_J_NORMAL, acc=ACC_J_NORMAL, sol=255)
        wait(0.5)

        movel(P_SCOOP_PICK, vel=VEL_X_SLOW, acc=ACC_X_SLOW, ref=DR_BASE)
        wait(0.3)

        set_digital_output(DO_GRIPPER_OPEN, OFF)
        wait(0.3)
        set_digital_output(DO_SCOOP_GRIP, ON)
        wait(1.5)

        movel(P_SCOOP_LIFT, vel=VEL_X_SLOW, acc=ACC_X_SLOW, ref=DR_BASE)
        wait(0.5)

        movejx(P_ICE_READY, vel=VEL_J_SLOW, acc=ACC_J_SLOW, sol=255)
        wait(1.0)

        node.get_logger().info(
            "1~5단계 완료. 스쿱 파지를 위해 DO1은 ON 상태입니다."
        )

    except KeyboardInterrupt:
        node.get_logger().warning("사용자가 실행을 중단했습니다.")
    except Exception as error:
        # 물체를 갑자기 떨어뜨리지 않도록 출력은 자동 초기화하지 않는다.
        node.get_logger().error("작업 중 오류 발생: " + repr(error))
        node.get_logger().warning(
            "그리퍼 출력은 자동 해제하지 않았습니다. 로봇과 물체 상태를 확인하세요."
        )
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main(sys.argv)
