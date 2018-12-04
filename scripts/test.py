#!/usr/bin/env python
from __future__ import print_function

import os
import subprocess as sp
import sys


CWD = os.path.dirname(os.path.realpath(__file__))
TOPDIR = os.path.realpath(os.path.join(CWD, os.pardir))
SRCDIR = os.path.join(TOPDIR, 'src')
PYTHONPATHEXT = [os.path.join(TOPDIR, '3rdparty', 'hdf5storage'), SRCDIR]
cmd_env = os.environ.copy()

if 'PYTHONPATH' in cmd_env:
    PYTHONPATHEXT.insert(cmd_env['PYTHONPATH'])
cmd_env['PYTHONPATH'] = os.pathsep.join(PYTHONPATHEXT)

print('TOPDIR=' + TOPDIR, file=sys.stderr)
print('PYTHONPATH=' + cmd_env['PYTHONPATH'], file=sys.stderr)

os.chdir(TOPDIR)
sp.check_call(['nosetests'])
sp.check_call(['python', os.path.join(SRCDIR, 'test_museplayer.py')],
              env=cmd_env)
