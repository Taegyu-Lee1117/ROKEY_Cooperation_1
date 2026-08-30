"""FastAPI 주문과 MakeIcecream Action을 연결하고 UI 피드백을 전달한다."""

import requests
import rclpy
from action_msgs.msg import GoalStatus
from icecream_interfaces.action import MakeIcecream
from icecream_interfaces.srv import AdminCommand
from dsr_msgs2.srv import MovePause, MoveResume, MoveStop
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


STEP_INFO = {
    "CUP_PICK": (10, "종이컵을 파지하고 있습니다."),
    "CUP_PLACE": (20, "종이컵을 제조 위치에 놓고 있습니다."),
    "SCOOP_PICK": (30, "스쿱을 파지하고 있습니다."),
    "MOVE_TO_ICECREAM": (45, "고정 아이스크림 위치로 이동하고 있습니다."),
    "SCOOP_ICECREAM": (60, "아이스크림을 스쿠핑하고 있습니다."),
    "PUT_ICECREAM_IN_CUP": (75, "아이스크림을 컵에 담고 있습니다."),
    "SCOOP_RETURN": (85, "스쿱을 반환하고 있습니다."),
    "SERVE_CUP": (95, "완성된 컵을 제공하고 있습니다."),
    "ORDER_COMPLETED": (100, "아이스크림 제공이 완료되었습니다."),
    "RETURN_HOME": (100, "로봇이 홈 위치로 복귀하고 있습니다."),
    "ROBOT_IDLE": (100, "로봇이 다음 주문을 기다립니다."),
}


class OrderBridge(Node):
    def __init__(self):
        super().__init__("order_bridge")
        self.declare_parameter("api_url", "http://127.0.0.1:8000")
        self.declare_parameter("poll_interval", 2.0)
        self.api_url = self.get_parameter("api_url").value.rstrip("/")
        self.action_client = ActionClient(self, MakeIcecream, "make_icecream")
        self.admin_client = self.create_client(AdminCommand, "/dsr01/admin_command")
        self.pause_client = self.create_client(MovePause, "/dsr01/dsr_controller2/motion/move_pause")
        self.resume_client = self.create_client(MoveResume, "/dsr01/dsr_controller2/motion/move_resume")
        self.stop_client = self.create_client(MoveStop, "/dsr01/dsr_controller2/motion/move_stop")
        self.active_order_id = None
        self.active_goal_handle = None
        self.active_admin_command_id = None
        self.pending_end = False
        self.current_step = ""
        self.timer = self.create_timer(self.get_parameter("poll_interval").value, self.poll_order)
        self.admin_timer = self.create_timer(0.5, self.poll_admin_command)

    def api(self, method, path, **kwargs):
        response = requests.request(method, self.api_url + path, timeout=3.0, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None

    def robot_state(self, status, order_id=None, step="", message=""):
        try:
            self.api("PATCH", "/robot/state", json={
                "status": status, "current_order_id": order_id,
                "current_step": step, "message": message,
            })
        except requests.RequestException as error:
            self.get_logger().error(f"로봇 상태 전송 실패: {error}")

    def order_feedback(self, status, step, progress, message):
        self.api("POST", f"/robot/orders/{self.active_order_id}/feedback", json={
            "status": status, "step": step, "progress": progress,
            "message": message, "eta_seconds": None,
        })

    def poll_order(self):
        if self.active_order_id is not None or not self.action_client.server_is_ready():
            return
        try:
            state = self.api("GET", "/robot/state")
            if state["status"] not in ("IDLE", "READY"):
                return
            order = self.api("GET", "/robot/orders/next")
            if order is None:
                return
            claimed = self.api("POST", f"/robot/orders/{order['id']}/claim")
        except requests.HTTPError as error:
            if error.response is not None and error.response.status_code == 409:
                return
            self.get_logger().error(f"주문 API 오류: {error}")
            return
        except requests.RequestException as error:
            self.get_logger().error(f"FastAPI 연결 실패: {error}")
            return
        self.active_order_id = claimed["id"]
        self.robot_state("PROCESSING", claimed["id"], message="주문 제조 시작")
        goal = MakeIcecream.Goal()
        goal.order_id = claimed["id"]
        goal.flavor_id = claimed["flavor_id"]
        goal.flavor_name = claimed["flavor_name"]
        future = self.action_client.send_goal_async(goal, feedback_callback=self.feedback_callback)
        future.add_done_callback(self.goal_response_callback)

    def finish_admin_command(self, success, message):
        command_id = self.active_admin_command_id
        if command_id is None:
            return
        try:
            self.api("PATCH", f"/robot/admin/commands/{command_id}/result", json={
                "status": "SUCCEEDED" if success else "FAILED", "message": message,
            })
        except requests.RequestException as error:
            self.get_logger().error(f"관리자 명령 결과 저장 실패: {error}")
        self.active_admin_command_id = None
        self.pending_end = False

    def poll_admin_command(self):
        if self.active_admin_command_id is not None:
            return
        try:
            command = self.api("GET", "/robot/admin/commands/next")
            if command is None:
                return
            command = self.api("POST", f"/robot/admin/commands/{command['id']}/claim")
        except requests.HTTPError as error:
            if error.response is not None and error.response.status_code == 409:
                return
            self.get_logger().error(f"관리자 명령 API 오류: {error}")
            return
        except requests.RequestException:
            return

        self.active_admin_command_id = command["id"]
        name = command["command"]
        if name == "START":
            self.handle_start_command()
        elif name == "PAUSE":
            self.handle_pause_command()
        elif name == "END":
            self.handle_end_command()
        elif self.active_order_id is not None:
            self.finish_admin_command(False, "제조 중에는 수동 제어 명령을 실행할 수 없습니다.")
        else:
            self.send_manual_command(name, command.get("joint_positions"))

    def handle_start_command(self):
        if self.active_order_id is None:
            self.robot_state("IDLE", None, message="자동 주문 처리 활성화")
            self.finish_admin_command(True, "자동 주문 처리를 시작했습니다.")
            return
        if not self.resume_client.service_is_ready():
            self.finish_admin_command(False, "로봇 재개 서비스를 사용할 수 없습니다.")
            return
        future = self.resume_client.call_async(MoveResume.Request())
        future.add_done_callback(self.resume_done)

    def resume_done(self, future):
        try:
            response = future.result()
            if not response.success:
                raise RuntimeError("두산 컨트롤러가 재개 요청을 거절했습니다.")
            self.robot_state("PROCESSING", self.active_order_id, self.current_step, "제조 동작 재개")
            self.finish_admin_command(True, "일시정지된 로봇 동작을 재개했습니다.")
        except Exception as error:
            self.finish_admin_command(False, f"재개 실패: {error}")

    def handle_pause_command(self):
        if self.active_order_id is None:
            self.robot_state("STOPPED", None, message="자동 주문 처리 일시정지")
            self.finish_admin_command(True, "자동 주문 처리를 일시정지했습니다.")
            return
        if not self.pause_client.service_is_ready():
            self.finish_admin_command(False, "로봇 일시정지 서비스를 사용할 수 없습니다.")
            return
        future = self.pause_client.call_async(MovePause.Request())
        future.add_done_callback(self.pause_done)

    def pause_done(self, future):
        try:
            response = future.result()
            if not response.success:
                raise RuntimeError("두산 컨트롤러가 일시정지 요청을 거절했습니다.")
            self.robot_state("STOPPED", self.active_order_id, self.current_step, "제조 동작 일시정지")
            self.finish_admin_command(True, "현재 로봇 동작을 일시정지했습니다.")
        except Exception as error:
            self.finish_admin_command(False, f"일시정지 실패: {error}")

    def handle_end_command(self):
        if self.active_order_id is None:
            self.send_manual_command("END", None)
            return
        if not self.stop_client.service_is_ready():
            self.finish_admin_command(False, "로봇 정지 서비스를 사용할 수 없습니다.")
            return
        self.pending_end = True
        request = MoveStop.Request()
        request.stop_mode = 2
        future = self.stop_client.call_async(request)
        future.add_done_callback(self.end_stop_done)

    def end_stop_done(self, future):
        try:
            response = future.result()
            if not response.success:
                raise RuntimeError("두산 컨트롤러가 종료 정지를 거절했습니다.")
            if self.active_goal_handle is None:
                raise RuntimeError("취소할 제조 Action handle이 없습니다.")
            self.active_goal_handle.cancel_goal_async()
            self.robot_state("STOPPED", self.active_order_id, self.current_step, "제조 종료 요청")
        except Exception as error:
            self.finish_admin_command(False, f"종료 실패: {error}")

    def send_manual_command(self, name, joint_positions):
        if not self.admin_client.service_is_ready():
            self.finish_admin_command(False, "관리자 ROS 서비스를 사용할 수 없습니다.")
            return
        request = AdminCommand.Request()
        request.command = name
        request.joint_positions = [0.0] * 6 if joint_positions is None else joint_positions
        future = self.admin_client.call_async(request)
        future.add_done_callback(self.manual_command_done)

    def manual_command_done(self, future):
        try:
            response = future.result()
            if response.success:
                self.robot_state("IDLE", None, message=response.message)
            else:
                self.robot_state("ERROR", None, message=response.message)
            self.finish_admin_command(response.success, response.message)
        except Exception as error:
            self.robot_state("ERROR", None, message=f"관리자 명령 실패: {error}")
            self.finish_admin_command(False, f"관리자 명령 실패: {error}")

    def feedback_callback(self, feedback_message):
        self.current_step = feedback_message.feedback.current_step
        progress, message = STEP_INFO.get(self.current_step, (0, self.current_step))
        order_status = "COMPLETED" if self.current_step in ("ORDER_COMPLETED", "RETURN_HOME", "ROBOT_IDLE") else "PROCESSING"
        robot_status = {"ORDER_COMPLETED": "RETURNING_HOME", "RETURN_HOME": "RETURNING_HOME", "ROBOT_IDLE": "IDLE"}.get(self.current_step, "PROCESSING")
        try:
            self.order_feedback(order_status, self.current_step, progress, message)
        except requests.RequestException as error:
            self.get_logger().error(f"진행 피드백 전송 실패: {error}")
        self.robot_state(robot_status, self.active_order_id, self.current_step, message)

    def goal_response_callback(self, future):
        try:
            handle = future.result()
            if not handle.accepted:
                self.finish_without_result("제조 Action Goal이 거절되었습니다.")
                return
            self.active_goal_handle = handle
            handle.get_result_async().add_done_callback(self.result_callback)
        except Exception as error:
            self.finish_without_result(f"Action Goal 전송 실패: {error}")

    def result_callback(self, future):
        try:
            wrapped = future.result()
            result = wrapped.result
            if self.pending_end:
                try:
                    self.order_feedback("FAILED", self.current_step, 0, "관리자가 제조 작업을 종료했습니다.")
                except requests.RequestException as error:
                    self.get_logger().error(f"종료 주문 상태 전송 실패: {error}")
                self.active_order_id = None
                self.active_goal_handle = None
                self.current_step = ""
                self.robot_state("RETURNING_HOME", None, message="종료 후 홈 복귀")
                self.send_manual_command("END", None)
                return
            if result.order_completed:
                self.order_feedback("COMPLETED", "SERVE_CUP", 100, "아이스크림 제공이 완료되었습니다.")
            if wrapped.status == GoalStatus.STATUS_SUCCEEDED and result.success and result.robot_ready:
                self.robot_state("IDLE", None, message="다음 주문 대기")
            else:
                self.report_failure(result)
        except Exception as error:
            self.finish_without_result(f"제조 결과 처리 실패: {error}")
            return
        self.active_order_id = None
        self.active_goal_handle = None
        self.current_step = ""

    def report_failure(self, result):
        if not result.order_completed:
            try:
                self.order_feedback("FAILED", result.process_step, 0, result.message)
            except requests.RequestException as error:
                self.get_logger().error(f"실패 상태 전송 불가: {error}")
        if not result.order_completed and result.process_step and result.error_code:
            try:
                self.api("POST", "/errors", json={
                    "order_id": self.active_order_id,
                    "process_step": result.process_step,
                    "error_code": result.error_code,
                    "message": result.message or "로봇 작업 실패",
                })
            except requests.RequestException as error:
                self.get_logger().error(f"오류 로그 저장 실패: {error}")
        self.robot_state("ERROR", self.active_order_id, result.process_step, result.message)

    def finish_without_result(self, message):
        if self.active_order_id is not None:
            try:
                self.order_feedback("FAILED", self.current_step, 0, message)
            except requests.RequestException:
                pass
        self.robot_state("ERROR", self.active_order_id, self.current_step, message)
        self.active_order_id = None
        self.active_goal_handle = None
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
