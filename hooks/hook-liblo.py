import pkg_resources
import sys

if sys.platform in ['darwin', 'linux', 'linux2']:
    liblo_path = pkg_resources.resource_filename('liblo', 'liblo.so')
    datas = [(liblo_path, '.')]
