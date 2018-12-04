@echo off
echo Make sure to run this from the root of the repo 1>&2
rmdir /s /q build
rmdir /s /q dist
copy /y 3rdparty\lo\0.28\win32-vs2008\lib\* src\
pyinstaller muse-player.spec