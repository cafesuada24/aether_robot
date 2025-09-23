FROM osrf/ros:foxy-desktop

SHELL ["/bin/bash", "-c"]

RUN apt update && apt install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-venv

WORKDIR /ros2_ws
COPY ./src ./src
COPY ./scripts ./scripts
COPY ./requirements.txt ./
# COPY ./venv ./venv

RUN source ./scripts/setup && \
    sudo rosdep fix-permissions && \
    rosdep update --rosdistro foxy && rosdep install --rosdistro foxy --from-paths src --ignore-src -r -y && \
    colcon build --packages-skip aether_gazebo object_tracker

RUN rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/bin/bash"]
