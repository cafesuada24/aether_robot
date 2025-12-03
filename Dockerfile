# FROM osrf/ros:jazzy-desktop
FROM arm64v8/ros:jazzy

SHELL ["/bin/bash", "-c"]

ENV DISPLAY=:0

RUN apt-get update && apt-get install -y \
    apt-utils \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-venv \
    sudo \
    vim \
    make

# COPY config/ /site_config/
COPY scripts/entrypoint.bash /entrypoint.bash

ARG DEFAULT_UERNAME=ubuntu
ARG USERNAME=$DEFAULT_USERNAME
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME >&/dev/null || echo "Group already exists" \
  && useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME >&/dev/null || echo "User already exists" \
  # && mkdir /home/$USERNAME/.config && chown $USER_UID:$USER_GID /home/$USERNAME/.config \
  && mkdir /home/$USERNAME/ros2_ws && chown $USER_UID:$USER_GID /home/$USERNAME/ros2_ws

RUN echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
  && chmod 0440 /etc/sudoers.d/$USERNAME

USER $USERNAME

COPY scripts/bashrc /home/$USERNAME/.bashrc

WORKDIR /home/$USERNAME/ros2_ws
COPY src src
COPY scripts/setup.bash scripts/setup.bash
# COPY ./requirements.txt ./
# COPY ./venv ./venv

RUN source /opt/ros/jazzy/setup.bash && \
    rosdep update --rosdistro jazzy && \
    rosdep install --rosdistro jazzy --from-paths src --ignore-src --skip-keys object_tracker -r -y

RUN apt-get install -y ros-jazzy-rmw-cyclonedds-cpp

RUN sudo rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/bin/bash", "/entrypoint.bash"]

CMD ["bash"]
