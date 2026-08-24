from setuptools import find_packages, setup

package_name = "roskin_robot"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="roskin team",
    maintainer_email="student@example.com",
    description="Roskin Robbins M0609 automation stages 1 to 5",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "icecream_1to5 = roskin_robot.icecream_1to5:main",
        ],
    },
)
