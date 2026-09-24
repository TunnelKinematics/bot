from setuptools import find_packages, setup

package_name = "bot_locomotion"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ahitagnied",
    maintainer_email="ad158@rice.edu",
    description="Converts /cmd_vel to joint commands.",
    license="Apache-2.0",
    extras_require={
        "test": [
            "pytest",
        ],
    },
    entry_points={
        "console_scripts": [
            "locomotion_node = bot_locomotion.locomotion_node:main"
        ],
    },
)
