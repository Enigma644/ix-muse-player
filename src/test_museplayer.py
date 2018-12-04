#!/usr/bin/python

import atexit
import datetime
import h5_eq
import hashlib
import os
import platform
import signal
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

MUSE_PLAYER = os.path.join(SCRIPT_DIR, 'muse-player.py')
TEST_DATA_DIR = os.path.realpath(
    os.path.join(SCRIPT_DIR, os.pardir, 'test_data'))

TIMEOUT_SECONDS = 60

if 'Windows' in platform.platform():
    ORIGINAL_DIR = os.path.join(TEST_DATA_DIR, 'win')
else:
    ORIGINAL_DIR = os.path.join(TEST_DATA_DIR, 'mac')


def try_run_muse(*args):
    start = datetime.datetime.now()
    proc = subprocess.Popen(('python', MUSE_PLAYER) + args)
    while proc.poll() is None:
        time.sleep(0.1)
        now = datetime.datetime.now()
        if (now - start).seconds > TIMEOUT_SECONDS:
            print >>sys.stderr, 'Timeout -- killed!'
            print >>sys.stderr, '#' * 80
            try:
                os.kill(proc.pid, signal.SIGTERM)
            finally:
                proc.wait()

def get_sha256(filename):
    return hashlib.sha256(open(filename, 'rb').read()).digest()

def get_size(filename):
    return os.stat(filename).st_size

def mk_match_fn(fn):
    def match_fn(filename1, filename2):
        r1 = fn(filename1)
        r2 = fn(filename2)
        return r1 == r2
    return match_fn

def run_():
    errors = []
    def check_matches(expected_filename, actual_filename, match_fn,
                      match_fail_msg):
        matched = None
        try:
            expected_path = os.path.join(ORIGINAL_DIR, expected_filename)
            actual_path = os.path.join(TEST_DATA_DIR, actual_filename)
            matched = match_fn(expected_path, actual_path)
            if not matched:
                errors.append(
                    '{} ({}, {})'.format(
                        match_fail_msg, expected_filename, actual_filename))
        except Exception as e:
            errors.append('Error computing results: ' + str(e))
        finally:
            print 'Matched: {} ({}, {})'.format(matched, expected_filename,
                                                actual_filename)
            return matched

    def check_sha256_matches(expected_filename, actual_filename):
        return check_matches(expected_filename, actual_filename,
                             mk_match_fn(get_sha256), 'SHA-256 mismatch')

    def check_size_matches(expected_filename, actual_filename):
        return check_matches(expected_filename, actual_filename,
                             mk_match_fn(get_size), 'Size mismatch')

    def check_hdf5_matches(expected_filename, actual_filename):
        return check_matches(expected_filename, actual_filename, h5_eq.files_match,
                             'HDF5 mismatch')

    start_time = time.time()

    try_run_muse('-f', os.path.join(TEST_DATA_DIR, 'muselab_recording.muse'),
                 '-F', os.path.join(TEST_DATA_DIR, 'checkMuseLab.muse'))
    try_run_muse('-f', os.path.join(TEST_DATA_DIR, 'muselab_recording.muse'),
                 '-M', os.path.join(TEST_DATA_DIR, 'checkMuseLabMatlab.mat'))
    try_run_muse('-f', os.path.join(TEST_DATA_DIR, 'muselab_recording.muse'),
                 '-C', os.path.join(TEST_DATA_DIR, 'checkMuseLabCSV.csv'))
    try_run_muse('-f', os.path.join(TEST_DATA_DIR, 'muselab_recording.muse'),
                 '-O', os.path.join(TEST_DATA_DIR, 'checkMuseLabOSC.osc'))

    try_run_muse('-o', os.path.join(TEST_DATA_DIR, 'raw_20sec.osc'),
                 '-F', os.path.join(TEST_DATA_DIR, 'checkRawOsc.muse'))

    check_sha256_matches('muselabtestoutput.muse', 'checkMuseLab.muse')
    check_hdf5_matches('muselabtestoutput.mat', 'checkMuseLabMatlab.mat')
    check_sha256_matches('muselabtestoutput.csv', 'checkMuseLabCSV.csv')
    check_sha256_matches('muselabtestoutput.osc', 'checkMuseLabOSC.osc')

    check_sha256_matches('rawtestoutput.muse', 'checkRawOsc.muse')

    print
    print 'Time to Run: ' + str(time.time()-start_time)
    if errors:
        print '\n'.join(['Errors: '] + errors)
        sys.exit(1)
    else: sys.exit(0)

if __name__ == '__main__':
    run_()
