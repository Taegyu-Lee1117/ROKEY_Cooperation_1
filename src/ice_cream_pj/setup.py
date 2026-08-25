from setuptools import find_packages, setup


package_name = "ice_cream_pj"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="dexy",
    maintainer_email="dexy@example.com",
    description="ROS 2 package for the ice cream project",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "first = ice_cream_pj.first:main",
            "order_bridge = ice_cream_pj.order_bridge:main",
        ],
    },
)
