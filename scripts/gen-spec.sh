#!/bin/sh
# Generates a new muse-player.spec.
#
# This should almost never need to be run, but is included for
# completeness' sake.
#
: ${PYINSTALLER:=pyinstaller}
cd "$(git rev-parse --show-toplevel)" &&
  { "$PYINSTALLER" --onefile \
                   --additional-hooks-dir=hooks \
                   --paths=src \
                   src/muse-player
    cat 1>&2 <<EOF

Make sure muse-player.spec doesn't refer to any machine-specific
paths. In particular, make sure pathex only mentions the src
relative path; it needn't also refer to the project directory.
EOF
  }
