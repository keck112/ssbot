#!/bin/bash
# SSBot Development Environment Setup for Ubuntu 24.04
# Run after fresh install: chmod +x setup_ubuntu.sh && ./setup_ubuntu.sh

set -e

echo "=== SSBot Ubuntu 24.04 Setup Script ==="

# 1. System Update
echo "[1/6] Updating system..."
sudo apt update && sudo apt upgrade -y

# 2. Intel Arc GPU drivers (already included in Ubuntu 24.04, but ensure latest)
echo "[2/6] Setting up Intel GPU..."
sudo apt install -y \
    intel-media-va-driver-non-free \
    mesa-utils \
    vulkan-tools \
    vainfo

# Verify GPU
echo "Checking GPU..."
glxinfo | grep "OpenGL renderer" || true

# 3. ROS 2 Jazzy Installation
echo "[3/6] Installing ROS 2 Jazzy..."
sudo apt install -y software-properties-common
sudo add-apt-repository universe -y
sudo apt update && sudo apt install -y curl

# Add ROS 2 GPG key
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

# Add ROS 2 repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
sudo apt install -y ros-jazzy-desktop

# 4. Gazebo Harmonic Installation
echo "[4/6] Installing Gazebo Harmonic..."
sudo apt install -y ros-jazzy-ros-gz

# 5. Development Tools
echo "[5/6] Installing development tools..."
sudo apt install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    git \
    build-essential \
    cmake

# Initialize rosdep
sudo rosdep init 2>/dev/null || true
rosdep update

# 6. Environment Setup
echo "[6/6] Configuring environment..."
echo "" >> ~/.bashrc
echo "# ROS 2 Jazzy" >> ~/.bashrc
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
echo "" >> ~/.bashrc
echo "# SSBot Workspace (uncomment after building)" >> ~/.bashrc
echo "# source ~/ssbot_ws/install/setup.bash" >> ~/.bashrc
echo "" >> ~/.bashrc
echo "# Gazebo Model Path" >> ~/.bashrc
echo "export GZ_SIM_RESOURCE_PATH=\$GZ_SIM_RESOURCE_PATH:~/ssbot_ws/src" >> ~/.bashrc

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Reboot to ensure GPU drivers are loaded"
echo "  2. Verify GPU: glxinfo | grep 'OpenGL renderer'"
echo "  3. Clone your ssbot repo to ~/ssbot_ws/src/"
echo "  4. Build: cd ~/ssbot_ws && colcon build"
echo "  5. Source: source ~/.bashrc"
echo "  6. Test: ros2 launch ssbot_bringup gazebo.launch.py"
echo ""
