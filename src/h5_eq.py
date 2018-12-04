"""
This is an equality comparator for hdf5 files.
"""
import h5py
import itertools
import numpy
import sys

def files_match(filename1, filename2):
    "Checks that two files have the same HDF5 structure."
    f1 = h5py.File(filename1, mode='r')
    f2 = h5py.File(filename2, mode='r')
    for k in iter(f1):
        # special case for the top level: skip randomly-generated refs
        if k in '#refs#':
            print >>sys.stderr, 'skip: ' + k
            continue
        print >>sys.stderr, 'check: ' + k
        if not subset(f1, f2, f1[k], f2[k], path=[k], verbose=True):
            return False
        if not subset(f2, f1, f2[k], f1[k], path=[k]):
            return False
    return True

def print_diff(a_v, b_v, path):
    print >>sys.stderr, '==> Diff found\n  a:{}\n  b:{}'.format(
        repr(a_v), repr(b_v))
    if path:
        print_path(path)

def print_path(path):
    print >>sys.stderr, 'path: ' + '/'.join(path)

def type_equiv(a, b):
    numpy_sints = [numpy.int8, numpy.int16, numpy.int32, numpy.int64]
    numpy_uints = [numpy.uint8, numpy.uint16, numpy.uint32, numpy.uint64]
    numpy_floats = [numpy.float, numpy.float64]
    return (a == b or
            (a in numpy_sints and b in numpy_sints) or
            (a in numpy_uints and b in numpy_uints) or
            (a in numpy_floats and b in numpy_floats))

def subset(f1, f2, a, b, path=None, verbose=False):
    """Returns true if object a in f1 is a subset of object b in f2.

    path, if passed, tracks the location within the HDF5 structure.
    """
    if not path:
        path = []
    a_t = type(a)
    b_t = type(b)

    if not type_equiv(a_t, b_t):
        print_diff(a_t, b_t, path)
        return False
    elif a_t == h5py.h5r.Reference:
        return subset(f1, f2, f1[a], f2[b], path + ['<r>'], verbose)
    elif a_t == h5py.Dataset:
        return subset(f1, f2, a.value, b.value, path + ['<d>'], verbose)
    elif a_t == numpy.ndarray:
        for i, (x, y) in enumerate(itertools.izip_longest(a, b)):
            cur = '<arr[{}]>'.format(i)
            if not subset(f1, f2, x, y, path + [cur], verbose):
                return False
        return True
    elif a_t in [numpy.int8, numpy.int16, numpy.int32, numpy.int64,
                 numpy.uint8, numpy.uint16, numpy.uint32, numpy.uint64,
                 numpy.float, numpy.float64]:
        if not a == b:
            print_diff(a, b, path)
            return False
        return True
    elif a_t == h5py._hl.group.Group:
        if verbose:
            print_path(path)
        for k in a.keys():
            cur = k
            if verbose:
                print >>sys.stderr, '  ' + str(k)
            if not k in b:
                print_diff(a[k], None, path + [cur])
                return False
            if not subset(f1, f2, a[k], b[k], path + [cur], verbose):
                return False
        return True
    else:
        print >>sys.stderr, 'Unknown type: ' + str(a_t)
        print_path(path)
        return False
