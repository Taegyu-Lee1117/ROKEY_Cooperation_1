import requests
import rclpy
from action_msgs.msg import GoalStatus
from icecream_interfaces.action import MakeIcecream
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class OrderBridge(Node):
    def __init__(self):
        super().__init__("order_bridge")
        self.declare_parameter("api_url", "http://127.0.0.1:8000")
        self.declare_parameter("poll_interval", 2.0)
        self.api_url = self.get_parameter("api_url").value.rstrip("/")
        poll_interval = self.get_parameter("poll_interval").value

        self.action_client = ActionClient(self, MakeIcecream, "make_icecream")
        self.active_order_id = None
        self.current_step = ""
        self.timer = self.create_timer(poll_interval, self.poll_order)
        self.get_logger().info(f"주문 API 연결 준비: {self.api_url}")

    def api_request(self, method, path, **kwargs):
        response = requests.request(
            method, f"{self.api_url}{path}", timeout=3.0, **kwargs
        )
        response.raise_for_status()
        return response.json() if response.content else None

    def poll_order(self):
        if self.active_order_id is not None:
            return
        if not self.action_client.server_is_ready():
            self.get_logger().warning(
                "make_icecream Action Server를 기다리는 중입니다.",
                throttle_duration_sec=10.0,
            )
            return

        try:
            order = self.api_request("GET", "/robot/orders/next")
            if order is None:
                return
            claimed = self.api_request(
                "POST", f"/robot/orders/{order['id']}/claim"
            )
        except requests.HTTPError as error:
            if error.response is not None and error.response.status_code == 409:
                return
            self.get_logger().error(f"주문 API 오류: {error}")
            return
        except requests.RequestException as error:
            self.get_logger().error(f"FastAPI 연결 실패: {error}")
            return

        self.active_order_id = claimed["id"]
        self.current_step = ""
        goal = MakeIcecream.Goal()
        goal.order_id = claimed["id"]
        goal.flavor_id = claimed["flavor_id"]
        goal.flavor_name = claimed["flavor_name"]
        self.get_logger().info(
            f"주문 #{goal.order_id} 수령: {goal.flavor_name}"
        )
        future = self.action_client.send_goal_async(
            goal, feedback_callback=self.feedback_callback
        )
        future.add_done_callback(self.goal_response_callback)

    def feedback_callback(self, feedback_message):
        self.current_step = feedback_message.feedback.current_step
        self.get_logger().info(
            f"주문 #{self.active_order_id} 단계: {self.current_step}"
        )

    def goal_response_callback(self, future):
        try:
            goal_handle = future.result()
        except Exception as error:
            self.finish_as_failed(f"Action Goal 전송 실패: {error}")
            return
        if not goal_handle.accepted:
            self.finish_as_failed("제조 Action Goal이 거절되었습니다.")
            return
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def result_callback(self, future):
        try:
            wrapped_result = future.result()
            result = wrapped_result.result
            if wrapped_result.status == GoalStatus.STATUS_SUCCEEDED and result.success:
                self.api_request(
                    "PATCH",
                    f"/orders/{self.active_order_id}/status",
                    json={"status": "COMPLETED"},
                )
                self.get_logger().info(f"주문 #{self.active_order_id} 완료")
            else:
                self.report_failure(result)
        except Exception as error:
            self.finish_as_failed(f"제조 결과 처리 실패: {error}")
            return
        self.active_order_id = None
        self.current_step = ""

    def report_failure(self, result):
        order_id = self.active_order_id
        self.api_request(
            "PATCH", f"/orders/{order_id}/status", json={"status": "FAILED"}
        )
        if result.process_step and result.error_code:
            self.api_request(
                "POST",
                "/errors",
                json={
                    "order_id": order_id,
                    "process_step": result.process_step,
                    "error_code": result.error_code,
                    "message": result.message or "로봇 제조 작업 실패",
                },
            )
        self.get_logger().error(f"주문 #{order_id} 실패: {result.message}")

    def finish_as_failed(self, message):
        order_id = self.active_order_id
        if order_id is not None:
            try:
                self.api_request(
                    "PATCH", f"/orders/{order_id}/status", json={"status": "FAILED"}
                )
            except requests.RequestException as error:
                self.get_logger().error(f"실패 상태 전송 불가: {error}")
        self.get_logger().error(message)
        self.active_order_id = None
        self.current_step = ""


def main(args=None):
    rclpy.init(args=args)
    node = OrderBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
