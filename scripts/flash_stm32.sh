#!/usr/bin/env bash
set -euo pipefail

FIRMWARE="${1:-firmware.elf}"

openocd -f interface/stlink.cfg -f target/stm32f4x.cfg \
  -c "program $FIRMWARE verify reset exit"

# Allow executing: chmod +x flash_stm32.sh
# Use: ./flash_stm32.sh firmware.elf