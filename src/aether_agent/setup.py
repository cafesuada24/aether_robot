import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'aether_agent'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*')),
    ],
    install_requires=[
        'setuptools',
        'semantic-kernel[google]',
        'dotenv',
        'typeguard',
        'dotenv',
        'catkin-pkg',
        'empy',
        'lark',
    ],
    zip_safe=True,
    maintainer='cafesuada',
    maintainer_email='108068915+cafesuada24@users.noreply.github.com',
    description='TODO: Package description',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'streamable_http_mcp_server = scripts.streamable_http_mcp_server:main',
            'llm_client = scripts.mcp_client:main',
        ],
    },
)
