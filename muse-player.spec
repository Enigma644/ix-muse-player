# -*- mode: python -*-
from sys import platform
if platform == 'win32':
    exe_name_ = 'muse-player.exe'
else:
    exe_name_ = 'muse-player'

a = Analysis(['src/muse-player.py'],
             pathex=[
                 '3rdparty/hdf5storage',
                 'src',
             ],
             hiddenimports=[],
             hookspath=['hooks'],
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=exe_name_,
          debug=False,
          strip=None,
          upx=True,
          console=True )
