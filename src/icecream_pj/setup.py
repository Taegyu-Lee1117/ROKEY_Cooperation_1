from glob import glob
from setuptools import find_packages, setup


package_name = "icecream_pj"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="dexy",
    maintainer_email="dexy@example.com",
    description="ROS 2 package for the ice cream project",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "order_bridge = icecream_pj.integrated_order_bridge:main",
            "make_icecream_server = icecream_pj.make_icecream_server:main",
        ],
    },
)
