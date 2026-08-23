import rclpy
import DR_init


ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"

# 두산 로봇의 직선 이동 단위는 mm입니다.
MOVE_DISTANCE_X = 50.0
VELOCITY = 10.0
ACCELERATION = 10.0

DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL


def main(args=None):
    rclpy.init(args=args)
    node = rclpy.create_node("first", namespace=ROBOT_ID)
    DR_init.__dsr__node = node

    try:
        from DSR_ROBOT2 import DR_BASE, DR_MV_MOD_REL, movel
        from DR_common2 import posx

        # 현재 위치에서 Base 좌표계의 +X 방향으로 50 mm 상대 이동합니다.
        relative_position = posx(MOVE_DISTANCE_X, 0.0, 0.0, 0.0, 0.0, 0.0)

        node.get_logger().info("Base +X 방향으로 50 mm 이동합니다.")
        movel(
            relative_position,
            vel=VELOCITY,
            acc=ACCELERATION,
            ref=DR_BASE,
            mod=DR_MV_MOD_REL,
        )
        node.get_logger().info("이동을 완료했습니다.")
    except Exception as error:
        node.get_logger().error(f"로봇 이동 실패: {error}")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
