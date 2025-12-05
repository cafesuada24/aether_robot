# FROM osrf/ros:jazzy-desktop
FROM ros:jazzy-ros-base

SHELL ["/bin/bash", "-c"]

ENV DISPLAY=:0

RUN apt-get update && apt-get install --no-install-recommends -y \
    apt-utils \
    python3-venv \
    vim \
    make \
    && rm -rf /var/lib/apt/lists/*

# COPY config/ /site_config/
COPY scripts/entrypoint.bash /entrypoint.bash

ARG DEFAULT_USERNAME=ubuntu
ARG USERNAME=$DEFAULT_USERNAME
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME >&/dev/null || echo "Group already exists" \
  && useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME >&/dev/null || echo "User already exists" \
  # && mkdir /home/$USERNAME/.config && chown $USER_UID:$USER_GID /home/$USERNAME/.config \
  && mkdir /home/$USERNAME/ros2_ws && chown $USER_UID:$USER_GID /home/$USERNAME/ros2_ws

RUN echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
  && chmod 0440 /etc/sudoers.d/$USERNAME


COPY scripts/bashrc /home/$USERNAME/.bashrc

WORKDIR /home/$USERNAME/ros2_ws
COPY src src
COPY scripts/setup.bash scripts/setup.bash
# COPY ./requirements.txt ./
# COPY ./venv ./venv

RUN source /opt/ros/jazzy/setup.bash && \
    rosdep update --rosdistro jazzy && \
    apt-get update && \
    rosdep install --rosdistro jazzy --from-paths src --ignore-src -r -y

RUN apt-get update && apt-get install -y ros-jazzy-rmw-cyclonedds-cpp && \
    rm -rf /var/lib/apt/lists/*

USER $USERNAME

ENTRYPOINT ["/bin/bash", "/entrypoint.bash"]

CMD ["bash"]
