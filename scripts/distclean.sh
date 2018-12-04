#!/bin/sh
# Removes the generated muse-player binary.
cd "$(git rev-parse --show-toplevel)" &&
  { rm -f dist/muse-player
    [ -d dist ] && rmdir dist
    [ ! -d dist ]
  }
