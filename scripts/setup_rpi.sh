#!/usr/bin/env bash
set -euo pipefail

echo "=== Raman RPi setup ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(realpath "$SCRIPT_DIR/..")"
WORK_DIR="$(realpath "$REPO_DIR/..")"
VENV_DIR="$WORK_DIR/venvs/raman"

sudo apt update
sudo apt full-upgrade -y

sudo apt install -y \
  git build-essential cmake ninja-build \
  python3 python3-pip python3-venv \
  minicom screen openocd usbutils

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip

if [ -f "$REPO_DIR/python/requirements.txt" ]; then
    pip install -r "$REPO_DIR/python/requirements.txt"
else
    pip install numpy scipy matplotlib pyserial pyqtgraph PySide6
fi

echo
echo "=== Checking USB devices ==="
lsusb || true

echo
echo "=== Checking serial devices ==="
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true

echo
echo "=== Setup completed ==="
echo "Repository : $REPO_DIR"
echo "Environment: $VENV_DIR"
echo
echo "To activate the virtual environment:"
echo "source $VENV_DIR/bin/activate"