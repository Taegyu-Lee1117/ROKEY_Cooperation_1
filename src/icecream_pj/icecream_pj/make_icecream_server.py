"""검증된 고정 모션을 실행하는 MakeIcecream Action Server."""

import threading
import DR_init
import rclpy
from icecream_interfaces.action import MakeIcecream
from icecream_interfaces.srv import AdminCommand
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from . import motion_config as cfg
from .cup import CupMotion
from .motion_common import MotionError, RobotController
from .scoop import ScoopMotion
from .serve import ServeMotion


DR_init.__dsr__id = cfg.ROBOT_ID
DR_init.__dsr__model = cfg.ROBOT_MODEL


class MakeIcecreamServer:
    def __init__(self, node, dr, posx, posj):
        self.node = node
        self.robot = RobotController(node, dr, posx, posj)
        self.cup = CupMotion(self.robot)
        self.scoop = ScoopMotion(self.robot)
        self.serve = ServeMotion(self.robot)
        self.busy_lock = threading.Lock()
        self.busy = False
        self.current_step = ""
        # 레인 순회 상태는 서버가 실행되는 동안 메모리에 유지한다.
        self.lane_idx = None
        self.lane_direction = 1
        self.server = ActionServer(
            node, MakeIcecream, "/make_icecream",
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
        )
        self.admin_service = node.create_service(
            AdminCommand, "admin_command", self.admin_command_callback
        )
        self.node.get_logger().info("make_icecream Action Server 준비 완료")

    def admin_command_callback(self, request, response):
        with self.busy_lock:
            if self.busy:
                response.success = False
                response.message = "제조 작업이 진행 중이어서 수동 명령을 실행할 수 없습니다."
                return response
            self.busy = True
        try:
            self.robot.prepare_manual_motion()
            command = request.command
            if command in ("HOME", "END"):
                self.cup.go_home()
            elif command == "CUP_PICK":
                self.robot.movejx_cup(cfg.P_CUP_APPROACH, "ADMIN_CUP_PICK", cfg.VEL_J_MANUAL, cfg.ACC_J_MANUAL)
            elif command == "CUP_PLACE":
                self.robot.movejx_cup(cfg.P_CUP_PLACE_APPROACH, "ADMIN_CUP_PLACE", cfg.VEL_J_MANUAL, cfg.ACC_J_MANUAL)
            elif command == "SCOOP_PICK":
                self.robot.movejx_scoop(cfg.P_SC_APP, "ADMIN_SCOOP_PICK", cfg.VEL_J_MANUAL, cfg.ACC_J_MANUAL)
            elif command == "ICECREAM":
                lane_1_approach = cfg.with_lane_dy(cfg.P_EN_APP, cfg.LANE_DY_LIST[0])
                self.robot.movejx_scoop(lane_1_approach, "ADMIN_ICECREAM_LANE_1", cfg.VEL_J_MANUAL, cfg.ACC_J_MANUAL)
            elif command == "SERVE_CUP":
                self.robot.movejx_cup(cfg.P_SERVE_APPROACH, "ADMIN_SERVE_CUP", cfg.VEL_J_MANUAL, cfg.ACC_J_MANUAL)
            elif command == "GRIPPER_OPEN":
                self.robot.open_gripper()
            elif command == "GRIPPER_CUP":
                self.robot.grip_cup()
            elif command == "GRIPPER_SCOOP":
                self.robot.grip_scoop()
            elif command == "MOVE_JOINTS":
                joints = [float(value) for value in request.joint_positions]
                if len(joints) != 6 or any(value < -180 or value > 180 for value in joints):
                    raise ValueError("관절값 6개가 -180~180도 범위여야 합니다.")
                self.robot.movej(joints, "ADMIN_MOVE_JOINTS", cfg.VEL_J_MANUAL, cfg.ACC_J_MANUAL)
            else:
                raise ValueError(f"지원하지 않는 관리자 명령: {command}")
            response.success = True
            response.message = f"{command} 명령을 완료했습니다."
        except Exception as error:
            response.success = False
            response.message = f"{request.command} 명령 실패: {error}"
            self.node.get_logger().error(response.message)
        finally:
            with self.busy_lock:
                self.busy = False
        return response

    def goal_callback(self, _goal_request):
        with self.busy_lock:
            if self.busy:
                return GoalResponse.REJECT
            self.busy = True
        return GoalResponse.ACCEPT

    def cancel_callback(self, _goal_handle):
        try:
            self.robot.soft_stop()
        except Exception as error:
            self.node.get_logger().error(f"Soft Stop 실패: {error}")
        return CancelResponse.ACCEPT

    @staticmethod
    def make_result(success=False, order_completed=False, robot_ready=False,
                    process_step="", error_code="", message=""):
        result = MakeIcecream.Result()
        result.success = success
        result.order_completed = order_completed
        result.robot_ready = robot_ready
        result.process_step = process_step
        result.error_code = error_code
        result.message = message
        return result

    def feedback(self, goal_handle, step):
        self.current_step = step
        feedback = MakeIcecream.Feedback()
        feedback.current_step = step
        goal_handle.publish_feedback(feedback)

    def _peek_next_lane(self):
        """상태를 변경하지 않고 다음 레인을 계산한다."""
        last_lane_index = len(cfg.LANE_DY_LIST) - 1
        if self.lane_idx is None:
            return 0, 1
        idx = self.lane_idx + self.lane_direction
        direction = self.lane_direction
        if idx == last_lane_index:
            direction = -1
        elif idx == 0:
            direction = 1
        return idx, direction

    def _commit_lane(self, idx, direction):
        self.lane_idx = idx
        self.lane_direction = direction

    def run_step(self, goal_handle, step, operation):
        if goal_handle.is_cancel_requested:
            goal_handle.canceled()
            raise MotionError(self.current_step or step, "UNKNOWN_ERROR", "작업이 취소되었습니다.")
        self.feedback(goal_handle, step)
        try:
            operation()
        except MotionError:
            raise
        except Exception as error:
            code = "SCOOP_FAILED" if step == "SCOOP_ICECREAM" else "MOVE_FAILED"
            raise MotionError(step, code, f"{step} 동작 실패: {error}") from error

    def execute_callback(self, goal_handle):
        order_completed = False
        try:
            goal = goal_handle.request
            self.node.get_logger().info(f"주문 #{goal.order_id} 시작: {goal.flavor_name}; 고정 제조 위치 사용")
            self.robot.wait(1.0)
            self.robot.init_robot()
            self.cup.go_home()
            home = self.robot._six(self.robot.dr.get_current_posj())
            if home is None:
                raise MotionError("CUP_PICK", "MOVE_FAILED", "홈 관절 위치를 읽지 못했습니다.")
            # 성공 전에는 레인 순회 상태를 변경하지 않는다.
            lane_idx, lane_direction = self._peek_next_lane()
            lane_dy = cfg.LANE_DY_LIST[lane_idx]
            self.node.get_logger().info(f"이번 주문 - 레인 {lane_idx + 1} (Y offset={lane_dy})")

            self.run_step(goal_handle, "CUP_PICK", self.cup.pick)
            self.run_step(goal_handle, "CUP_PLACE", self.cup.place)
            self.run_step(goal_handle, "SCOOP_PICK", self.scoop.pick)
            self.run_step(goal_handle, "MOVE_TO_ICECREAM", lambda: self.scoop.move_to_icecream(lane_dy))
            self.run_step(goal_handle, "SCOOP_ICECREAM", lambda: self.scoop.scoop(lane_dy))
            self.run_step(goal_handle, "PUT_ICECREAM_IN_CUP", lambda: self.scoop.put_in_cup(lane_dy))
            self._commit_lane(lane_idx, lane_direction)
            self.run_step(goal_handle, "SCOOP_RETURN", self.scoop.return_scoop)
            self.run_step(goal_handle, "SERVE_CUP", self.serve.serve)
            order_completed = True
            self.feedback(goal_handle, "ORDER_COMPLETED")
            self.run_step(goal_handle, "RETURN_HOME", lambda: self.serve.return_home(home[5]))
            self.feedback(goal_handle, "ROBOT_IDLE")
            goal_handle.succeed()
            return self.make_result(True, True, True, message="제조와 홈 복귀가 완료되었습니다.")
        except MotionError as error:
            if not goal_handle.is_cancel_requested:
                goal_handle.abort()
            return self.make_result(False, order_completed, False, error.process_step, error.error_code, error.message)
        except Exception as error:
            goal_handle.abort()
            message = f"알 수 없는 제조 오류: {error}"
            return self.make_result(False, order_completed, False, self.current_step, "UNKNOWN_ERROR", message)
        finally:
            with self.busy_lock:
                self.busy = False
            self.current_step = ""

    def destroy(self):
        self.node.destroy_service(self.admin_service)
        self.server.destroy()


def main(args=None):
    rclpy.init(args=args)
    action_node = rclpy.create_node("make_icecream_server", namespace=cfg.ROBOT_ID)
    robot_node = rclpy.create_node("make_icecream_robot_api", namespace=cfg.ROBOT_ID)
    # 동기 로봇 API와 Action Server가 서로의 executor를 방해하지 않도록 분리한다.
    DR_init.__dsr__node = robot_node
    import DSR_ROBOT2 as dr
    from DR_common2 import posj, posx
    server = MakeIcecreamServer(action_node, dr, posx, posj)
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(action_node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        server.destroy()
        action_node.destroy_node()
        robot_node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
