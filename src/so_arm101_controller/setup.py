from setuptools import setup

package_name = 'so_arm101_controller'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='robot',
    maintainer_email='robot@todo.todo',
    description='SO ARM 101 Controller Package',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'arm_node = so_arm101_controller.arm_node:main',
            'vision_tracker_node = so_arm101_controller.vision_tracker_node:main',
            'vision_tracker_ocr = so_arm101_controller.vision_tracker_ocr:main',
            'main_node = so_arm101_controller.main:main',
        ],
    },
)