from Muse_v1 import *
import struct
import json
import google.protobuf.internal.containers
import threading
import time
import Queue


class MuseProtoBufReaderV1(object):

    def __init__(self, verbose=False):
        self.events = []
        self.__objects = []
        self.__config_id = 0
        self.thread_lock = threading.Lock()
        self.__verbose = verbose
        self.__timestamp = 0
        self.added_to_events = 0
        self.events_queue = Queue.Queue()

    def parse(self, in_stream):

        while True:
            # (1) Read the message header
            header_bin = in_stream.read(4)
            # check for EOF
            if len(header_bin) == 0:
                self.add_done()
                break

            header = struct.unpack("<i", header_bin)
            msg_length = header[0]
            msg_type = in_stream.read(2)
            msg_type = struct.unpack("<h", msg_type)
            msg_type = msg_type[0]
            if msg_type != 1:
                if self.__verbose:
                    print 'Corrupted file, type mismatch. Parsed: ' + str(msg_type) + ' expected 1'
                self.add_done()
                break

            # (2) Read and parse the message
            msg_bin = in_stream.read(msg_length)
            if len(msg_bin) != msg_length:
                if self.__verbose:
                    print 'Corrupted file: ' + str(in_stream) + ', length mismatch. Reporting length: ' + str(len(msg_bin)) + ' expected: ' + str(msg_length)
                self.add_done()
                break

            muse_data_collection = MuseDataCollection()
            muse_data_collection.ParseFromString(msg_bin)

            # (3) Process this chunk of data
            self.__objects.extend(muse_data_collection.collection)
 
            for obj in self.__objects:
                self.__handle_data(obj)

            self.__objects = []

    def add_done(self):
        self.add_to_events_queue([self.__timestamp + 0.001, 'done'])


    # dispatch based on data type
    def __handle_data(self, md):
        # Version 2 response
        # Configuration data
        if md.datatype == MuseData.CONFIG:
            data_obj = md.Extensions[MuseConfig.museData]
            self.handle_config(md.timestamp, data_obj)

        # Version
        if md.datatype == MuseData.VERSION:
            data_obj = md.Extensions[MuseVersion.museData]
            self.handle_version(md.timestamp, data_obj)

        # EEG samples
        if md.datatype == MuseData.EEG:
            data_obj = md.Extensions[MuseEEG.museData]
            # Check if this is a DRL/REF message
            if data_obj.HasField("drl"):
                self.handle_drlref(md.timestamp, data_obj)
            else:
                self.handle_eeg(md.timestamp, data_obj)

        # Quantization data
        if md.datatype == MuseData.QUANT:
            data_obj = md.Extensions[MuseQuantization.museData]
            self.handle_quantization(md.timestamp, data_obj)

        # Accelerometer
        if md.datatype == MuseData.ACCEL:
            data_obj = md.Extensions[MuseAccelerometer.museData]
            self.handle_acc(md.timestamp, data_obj)

        # Battery
        if md.datatype == MuseData.BATTERY:
            data_obj = md.Extensions[MuseBattery.museData]
            self.handle_batt(md.timestamp, data_obj)

        # Annotations
        if md.datatype == MuseData.ANNOTATION:
            data_obj = md.Extensions[MuseAnnotation.museData]
            self.handle_annotation(md.timestamp, data_obj)

    def handle_json_dictionary_from_proto(self, data_obj):
        m = {}
        for a in dir(data_obj):
            upper_flag = False
            if a.startswith('_'):
                continue
            for x in a:
                if x.isupper():
                    upper_flag = True
                    break
            if upper_flag:
                continue
            value = getattr(data_obj, a)
            if isinstance(value, google.protobuf.internal.containers.RepeatedScalarFieldContainer):
                temp = []
                temp.extend(value)
                value = temp
            m[a] = value
        return json.dumps(m)

    def handle_config(self, timestamp, data_obj):
        json_dict = self.handle_json_dictionary_from_proto(data_obj)
        self.add_to_events_queue([timestamp, "/muse/config", "s", [str(json_dict)],
                            self.__config_id])

    def handle_version(self, timestamp, data_obj):
        json_dict = self.handle_json_dictionary_from_proto(data_obj)
        self.add_to_events_queue([timestamp, "/muse/version", "s", [str(json_dict)],
                            self.__config_id])

    def handle_eeg(self, timestamp, data_obj):
        # Check if this is a 6 channel EEG message
        if data_obj.HasField("left_aux"):
            self.add_to_events_queue([timestamp, "/muse/eeg/raw", "ffffff",
                                  [data_obj.left_aux,
                                   data_obj.left_ear,
                                   data_obj.left_forehead,
                                   data_obj.right_forehead,
                                   data_obj.right_ear,
                                   data_obj.right_aux],
                            self.__config_id])
        else:
            self.add_to_events_queue([timestamp, "/muse/eeg/raw", "ffff",
                                  [data_obj.left_ear,
                                   data_obj.left_forehead,
                                   data_obj.right_forehead,
                                   data_obj.right_ear],
                            self.__config_id])

    def handle_drlref(self, timestamp, data_obj):
        self.add_to_events_queue([timestamp, "/muse/drlref/raw", "ff",
                            [data_obj.drl,
                             data_obj.ref],
                            self.__config_id])

    def handle_quantization(self, timestamp, data_obj):
        self.add_to_events_queue([timestamp, "/muse/eeg/quantization", "iiii",
                            [data_obj.left_ear,
                             data_obj.left_forehead,
                             data_obj.right_forehead,
                             data_obj.right_ear],
                            self.__config_id])

    def handle_acc(self, timestamp, data_obj):
        self.add_to_events_queue([timestamp, "/muse/acc/raw", "iii",
                            [data_obj.acc1,
                             data_obj.acc2,
                             data_obj.acc3],
                            self.__config_id])

    def handle_batt(self, timestamp, data_obj):
        self.add_to_events_queue([timestamp, "/muse/batt/raw", "iiii",
                            [data_obj.percent_remaining,
                             data_obj.battery_fuel_gauge_millivolts,
                             data_obj.battery_adc_millivolts,
                             data_obj.temperature_celsius],
                            self.__config_id])

    def handle_annotation(self, timestamp, data_obj):
        # TODO Handle known annotations
        self.add_to_events_queue([timestamp, "/muse/annotation", "sssss", [data_obj.event_data,
                                                                     data_obj.event_type,'','',''],
                            self.__config_id])

    def add_to_events_queue(self, event):
        self.__timestamp = event[0]
        self.events_queue.put(event)
        self.added_to_events += 1

        while self.events_queue.qsize() >= 30000:
            time.sleep(0)
