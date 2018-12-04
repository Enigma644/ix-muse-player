#!/bin/sh
# Builds dist/muse-player.
: ${PYINSTALLER:=pyinstaller}
cd "$(git rev-parse --show-toplevel)" &&
  "$PYINSTALLER" muse-player.spec
