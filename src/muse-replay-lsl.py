#!/usr/bin/python

import pylsl
import time
from optparse import OptionParser
from muse_data_handler import *


# Broadcasts Muse data messages over labstreaminglayer
class MuseDataLslHandler(MuseDataHandler):
    def __init__(self):
        self.__outlets = {}
        self.__events = []

    @staticmethod
    def __scale(raw_value):
        # scaling from nanovolts to microvolts
        return raw_value / 1000.0

    def handle_config(self, timestamp, data_obj):

        # Configure the LSL streams
        eeg_info = pylsl.stream_info("Interaxon","EEG", data_obj.eeg_channel_count,
                                     data_obj.eeg_sample_frequency_hz, pylsl.cf_float32,
                                     "Muse-EEG-" + data_obj.mac_addr)
        eeg_info.desc().append_child_value("manufacturer", "Interaxon")
        channels = eeg_info.desc().append_child("channels")
        for c in data_obj.eeg_channel_layout.split():
            channels.append_child("channel").append_child_value("label",c).append_child_value("unit","microvolts").append_child_value("type","EEG")

        # outgoing buffer size to 360 seconds (max.) and the transmission chunk size to 32 samples
        self.__outlets["EEG"] = pylsl.stream_outlet(eeg_info, 360, 32)


        acc_info = pylsl.stream_info("Interaxon","Accelerometer", 3, 50, pylsl.cf_int32,
                                     "Muse-AC-" + data_obj.mac_addr)
        acc_info.desc().append_child_value("manufacturer", "Interaxon")
        channels = acc_info.desc().append_child("channels")
        for c in ['x', 'y', 'z']:
            channels.append_child("channel").append_child_value("label",c).append_child_value("unit","4/1023g").append_child_value("type","Accelerometer")

        # outgoing buffer size to 360 seconds (max.) and the transmission chunk size to 32 samples
        self.__outlets["ACC"] = pylsl.stream_outlet(acc_info, 360, 32)


    def handle_eeg(self, timestamp, data_obj):
        # Check if this is a 6 channel EEG message
        if data_obj.HasField("left_aux"):
            self.__events.append([timestamp, "EEG",
                                  [self.__scale(data_obj.left_aux),
                                   self.__scale(data_obj.left_ear),
                                   self.__scale(data_obj.left_forehead),
                                   self.__scale(data_obj.right_forehead),
                                   self.__scale(data_obj.right_ear),
                                   self.__scale(data_obj.right_aux)]])
        else:
            self.__events.append([timestamp, "EEG",
                                  [self.__scale(data_obj.left_ear),
                                   self.__scale(data_obj.left_forehead),
                                   self.__scale(data_obj.right_forehead),
                                   self.__scale(data_obj.right_ear)]])

    def handle_acc(self, timestamp, data_obj):
        self.__events.append([timestamp, "ACC",
                              [data_obj.acc1,
                               data_obj.acc2,
                               data_obj.acc3]])

    # Replays LSL messages. Optionally in real time
    def replay(self, live=True):

        if len(self.__outlets) == 0:
            raise "Configuration missing."

        if len(self.__events) == 0:
            return

        # (1) get the current time
        delta = time.time() - self.__events[0][0]

        # (2) Loop over messages
        for m in self.__events:
            # (3) Wait until the time is right. and send.
            time_to_wait = m[0] + delta - time.time()
            if time_to_wait > 0 and live:
                time.sleep(time_to_wait)

            samples = pylsl.vectorf(m[2])
            self.__outlets[m[1]].push_sample(samples)


# If invoked as a script
if __name__ == "__main__":

    usage = "usage: %prog [options] inputFile(s)"
    parser = OptionParser(usage=usage)

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                  help="print status messages to stdout")
    parser.add_option("-l", "--live", action="store_true", dest="live", default=False,
                  help="replay LSL messages in real time")

    (options, args) = parser.parse_args()

    if len(args) == 0:
        print "Error: Missing input file(s)"
        parser.print_help()
        sys.exit(-1)

    # parse the input files
    lsl = MuseDataLslHandler()
    lsl.parse_files(args, verbose=options.verbose)

    # replay
    if options.verbose:
        print "Replaying over LSL"

    lsl.replay(live=options.live)



