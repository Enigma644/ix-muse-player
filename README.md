# Muse Player v1.9.1

Modified version of [Interaxon's Muse Player](https://bitbucket.org/interaxon/museplayer)

[IX-README](README-IX.md)

## Bug Fixes / Changes

* UTF-8 support for CSV [-C]
* UTF-8 support for OSC [-O]
* Increased accuracy for OSC output (removed 6dp limit)

## Build process

* Copy https://bitbucket.org/interaxon/3rdparty_liblo.git to 3rdparty\lo
* Copy https://github.com/frejanordsiek/hdf5storage to 3rdparty\hdf5storage
* Open command prompt and navigate to the project root
* Run ```scripts\winbuild.bat```
* exe will be generated in ```dist``` folder

## Binary

If you just want the compiled binary, that is available here: [muse-player.exe](dist/muse-player.exe)