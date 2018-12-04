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


class DumpOSC:

    def blob_to_hex(self, b):
        return " ".join([ (hex(v/16).upper()[-1] + hex(v%16).upper()[-1]) for v in b ])

    def callback(self, path, args, types, src):
        write = sys.stdout.write
        ## print source
        #write("from " + src.get_url() + ": ")
        # print path
        write(path + " ,")
        # print typespec
        write(types)
        # loop through arguments and print them
        for a, t in zip(args, types):
            write(" ")
            if t == None:
                #unknown type
                write("[unknown type]")
            elif t == 'b':
                # it's a blob
                write("[" + self.blob_to_hex(a) + "]")
            else:
               # anything else
                write(str(a))
        write('\n')

    def __init__(self, port = None):
        # create server object
        try:
            self.server = liblo.Server(port)
        except liblo.ServerError, err:
            sys.exit(str(err))

        print "listening on URL: " + self.server.get_url()

        # register callback function for all messages
        self.server.add_method(None, None, self.callback)

    def run(self):
        # just loop and dispatch messages every 10ms
        while True:
            self.server.recv(10)


if __name__ == '__main__':
    # display help
    if len(sys.argv) == 1 or sys.argv[1] in ("-h", "--help"):
        sys.exit("Usage: " + sys.argv[0] + " port")

    # require one argument (port number)
    if len(sys.argv) < 2:
        sys.exit("please specify a port or URL")

    app = DumpOSC(sys.argv[1])
    try:
        app.run()
    except KeyboardInterrupt:
        del app
