#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# pyliblo - Python bindings for the liblo OSC library
#
# Copyright (C) 2007-2011  Dominic Sacré  <dominic.sacre@gmx.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#

import sys
import liblo


def make_message_auto(path, *args):
    msg = liblo.Message(path)

    for a in args:
        try: v = int(a)
        except ValueError:
            try: v = float(a)
            except ValueError:
                v = a
        msg.add(v)

    return msg


def make_message_manual(path, types, *args):
    if len(types) != len(args):
        sys.exit("length of type string doesn't match number of arguments")

    msg = liblo.Message(path)
    try:
        for a, t in zip(args, types):
            msg.add((t, a))
    except Exception, e:
        sys.exit(str(e))

    return msg


if __name__ == '__main__':
    # display help
    if len(sys.argv) == 1 or sys.argv[1] in ("-h", "--help"):
        sys.exit("Usage: " + sys.argv[0] + " port path [,types] [args...]")

    # require at least two arguments (target port/url and message path)
    if len(sys.argv) < 2:
        sys.exit("please specify a port or URL")
    if len(sys.argv) < 3:
        sys.exit("please specify a message path")

    if len(sys.argv) > 3 and sys.argv[3].startswith(','):
        msg = make_message_manual(sys.argv[2], sys.argv[3][1:], *sys.argv[4:])
    else:
        msg = make_message_auto(*sys.argv[2:])

    try:
        liblo.send(sys.argv[1], msg)
    except IOError, e:
        sys.exit(str(e))
    else:
        sys.exit(0)
