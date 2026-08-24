# 로스킨라빈스 ROS2 실행 패키지

## 환경

- Ubuntu 24.04
- ROS 2 Jazzy
- Doosan M0609
- 로봇 이름/네임스페이스: `dsr01`
- 두산 공식 `doosan-robot2` 설치 및 빌드 완료 상태

## 설치

```bash
source /opt/ros/jazzy/setup.bash
mkdir -p ~/ros2_ws/src
cp -r roskin_robot_ros2 ~/ros2_ws/src/roskin_robot
cd ~/ros2_ws
rosdep install -r --from-paths src --ignore-src -y
colcon build --symlink-install --packages-select roskin_robot
source install/setup.bash
```

## 실제 로봇 연결

로봇 제어기 IP가 `192.168.137.100`인 예시입니다. 현장 IP가 다르면 변경합니다.

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 launch dsr_bringup2 dsr_bringup2_rviz.launch.py \
  mode:=real \
  host:=192.168.137.100 \
  port:=12345 \
  model:=m0609 \
  name:=dsr01
```

## 작업 노드 실행

새 터미널에서 실행합니다.

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run roskin_robot icecream_1to5
```

## 실행 전 확인

1. 티칭팬던드가 자동 운전 가능한 상태인지 확인합니다.
2. 비상정지 버튼 위치를 확인합니다.
3. WebLogic 프로그램이 실행 중인지 확인합니다.
4. 컨트롤박스 DO1/DO2/DO3가 Compute Box 입력 1/2/3과 연결되는지 확인합니다.
5. 컵과 스쿱을 제거하고 로봇 속도 10% 이하에서 먼저 시험합니다.
6. `P_CUP_EXIT_SAFE`는 계산 좌표이므로 특히 저속으로 확인합니다.

## I/O 대응

- DO1: 스쿱 파지
- DO2: 그리퍼 열기
- DO3: 컵 파지 68 mm / 3 N

## 중요

- DART와 ROS2 프로그램을 동시에 실행하지 않습니다.
- ROS2 실행 중 DART Task를 시작하지 않습니다.
- 오류 시 물체가 떨어지는 것을 방지하기 위해 프로그램이 그리퍼 출력을 자동 해제하지 않습니다.
- `SetSingularityHandlingForce` ImportError가 발생하면 사용자 패키지 문제가 아니라 `doosan-robot2`의 `DSR_ROBOT2.py`와 `dsr_msgs2` 빌드 결과가 서로 맞지 않는 상태일 가능성이 큽니다.
