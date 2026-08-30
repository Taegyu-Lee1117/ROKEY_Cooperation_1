import rclpy
import DR_init

ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"

# 홈 관절 좌표 (J1~J6, degree)
HOME_POSITION = (0.01, -0.01, 90.05, -0.02, 89.95, 0.01)

# 최초 실기동을 위한 저속 설정 (degree/s, degree/s^2)
HOME_VELOCITY = 5.0
HOME_ACCELERATION = 5.0

DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL

def main(args=None):
    rclpy.init(args=args)
    node = rclpy.create_node("home_return", namespace=ROBOT_ID)
    DR_init.__dsr__node = node

    try:
        from DSR_ROBOT2 import movej
        from DR_common2 import posj

        home_position = posj(*HOME_POSITION)

        node.get_logger().info(f"홈 위치로 이동합니다: {HOME_POSITION}")
        result = movej(
            home_position,
            vel=HOME_VELOCITY,
            acc=HOME_ACCELERATION,
        )

        if result != 0:
            raise RuntimeError(f"movej 실패 코드: {result}")

        node.get_logger().info("홈 위치 이동을 완료했습니다.")
    except Exception as error:
        node.get_logger().error(f"홈 복귀 실패: {error}")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
