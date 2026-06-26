#!/bin/bash
# Build (if needed) and run the Tiny-Rails-but-tinier dual-PPU train sim.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/dual-ppu-mesen/bin/osx-arm64/Release/osx-arm64/publish/Mesen.app"
python3 "$DIR/tools/gen.py"          # regenerate art/levels
make -C "$DIR" all                   # assemble ROM
caffeinate -u -t 2 2>/dev/null || true   # wake display (Mesen needs it)
open "$APP" --args "$DIR/bin/parallax.nes"
echo "Running. Controls: Right=throttle/express, Left=brake. It self-drives by default."
