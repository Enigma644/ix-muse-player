#!/bin/sh
# Cleans up files generated in the build process.
cd "$(git rev-parse --show-toplevel)" &&
  { rm -rf build &&
    find . -type f -name \*.pyc -print0 | xargs -0 rm -f &&
    find test_data -type f -name check* -print0 | xargs -0 rm -f
  }
