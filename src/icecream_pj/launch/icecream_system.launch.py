"""Launch only the ROS 2 parts of the ice cream robot system."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    mode = LaunchConfiguration("mode")
    host = LaunchConfiguration("host")
    port = LaunchConfiguration("port")
    model = LaunchConfiguration("model")
    robot_name = LaunchConfiguration("name")
    api_url = LaunchConfiguration("api_url")

    robot_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(
                Path(get_package_share_directory("dsr_bringup2"))
                / "launch"
                / "dsr_bringup2_rviz.launch.py"
            )
        ),
        launch_arguments={
            "mode": mode,
            "host": host,
            "port": port,
            "model": model,
            "name": robot_name,
        }.items(),
    )

    make_icecream_server = TimerAction(
        period=8.0,
        actions=[
            Node(
                package="icecream_pj",
                executable="make_icecream_server",
                output="screen",
            )
        ],
    )

    order_bridge = TimerAction(
        period=10.0,
        actions=[
            Node(
                package="icecream_pj",
                executable="order_bridge",
                parameters=[{"api_url": api_url}],
                output="screen",
            )
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("mode", default_value="real"),
            DeclareLaunchArgument("host", default_value="192.168.1.100"),
            DeclareLaunchArgument("port", default_value="12345"),
            DeclareLaunchArgument("model", default_value="m0609"),
            DeclareLaunchArgument("name", default_value="dsr01"),
            DeclareLaunchArgument(
                "api_url", default_value="http://127.0.0.1:8000"
            ),
            robot_bringup,
            make_icecream_server,
            order_bridge,
        ]
    )
