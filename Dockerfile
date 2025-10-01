FROM arm64v8/ros:jazzy

SHELL ["/bin/bash", "-c"]

RUN apt update && apt install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-venv

WORKDIR /ros2_ws
COPY ./src ./src
COPY ./scripts ./scripts
# COPY ./requirements.txt ./
COPY ./venv ./venv

RUN source ./scripts/setup.bash && \
    rosdep update --rosdistro jazzy --ignore-packages aether_gazebo && \
    rosdep install --rosdistro jazzy --from-paths src --ignore-packages aether_gazebo --ignore-src -r -y && \
    colcon build --packages-ignore aether_gazebo
RUN rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/bin/bash"]
