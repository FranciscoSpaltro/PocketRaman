#!/usr/bin/env bash
set -euo pipefail

echo "=== Raman RPi setup ==="

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$HOME/venvs/raman"

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

if [ -f "$REPO_DIR/requirements.txt" ]; then
  pip install -r "$REPO_DIR/requirements.txt"
else
  pip install numpy scipy matplotlib pyserial pyqtgraph PySide6
fi

echo "Done."

echo
echo "=== Checking USB devices ==="
lsusb || true

echo
echo "=== Checking serial devices ==="
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true

echo "Repo: $REPO_DIR"
echo "Venv: $VENV_DIR"
echo "Activate with:"
echo "source $VENV_DIR/bin/activate"