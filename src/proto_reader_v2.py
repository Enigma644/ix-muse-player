from Muse_v2 import *
import struct
import json
import google.protobuf.internal.containers
import threading
import time
import Queue


class MuseProtoBufReaderV2(object):

    def __init__(self, verbose):
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
            if msg_type != 2:
                print 'Corrupted file, type mismatch. Parsed: ' + str(msg_type) + ' expected 2'
                self.add_done()
                break

            # (2) Read and parse the message
            msg_bin = in_stream.read(msg_length)
            if len(msg_bin) != msg_length:
                print 'Corrupted file, length mismatch. Reporting length: ' + str(len(msg_bin)) + ' expected: ' + str(msg_length)
                self.add_done()
                break

            muse_data_collection = MuseDataCollection()
            muse_data_collection.ParseFromString(msg_bin)

            # (3) Process this chunk of data
            self.__objects.extend(muse_data_collection.collection)

            for obj in self.__objects:
                self.handle_data(obj)

            self.__objects = []

    def add_done(self):
        self.add_to_events_queue([self.__timestamp + 0.001, 'done'])

    # dispatch based on data type
    def handle_data(self, md):
        # Version 2 response
        # Configuration data
        self.__config_id = md.config_id
        if md.datatype == MuseData.CONFIG:
            data_obj = md.Extensions[MuseConfig.museData]
            self.handle_config(md.timestamp, data_obj)

        # Version
        if md.datatype == MuseData.VERSION:
            data_obj = md.Extensions[MuseVersion.museData]
            self.handle_version(md.timestamp, data_obj)

        # EEG samples
        if md.datatype == MuseData.EEG:
            data_obj = md.Extensions[EEG.museData]
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
            data_obj = md.Extensions[Accelerometer.museData]
            self.handle_acc(md.timestamp, data_obj)

        # Battery
        if md.datatype == MuseData.BATTERY:
            data_obj = md.Extensions[Battery.museData]
            self.handle_batt(md.timestamp, data_obj)

        # Annotations
        if md.datatype == MuseData.ANNOTATION:
            data_obj = md.Extensions[Annotation.museData]
            self.handle_annotation(md.timestamp, data_obj)

        # DSP
        if md.datatype == MuseData.DSP:
            data_obj = md.Extensions[DSP.museData]
            self.handle_dsp(md.timestamp, data_obj)

        # ComputingDevice
        if md.datatype == MuseData.COMPUTING_DEVICE:
            data_obj = md.Extensions[ComputingDevice.museData]
            self.handle_computing_device(md.timestamp, data_obj)

        # EEG Dropped
        if md.datatype == MuseData.EEG_DROPPED:
            data_obj = md.Extensions[EEG_DroppedSamples.museData]
            self.handle_dropped_eeg(md.timestamp, data_obj)

        # Acc Dropped
        if md.datatype == MuseData.ACC_DROPPED:
            data_obj = md.Extensions[ACC_DroppedSamples.museData]
            self.handle_dropped_acc(md.timestamp, data_obj)

    def handle_json_dictionary_from_proto(self, data_obj):
        m={}
        for a in dir(data_obj):
            upperFlag = False
            if a.startswith('_'):
                continue
            for x in a:
                if x.isupper():
                    upperFlag = True
                    break
            if upperFlag:
                continue
            value = getattr(data_obj,a)
            if isinstance(value, google.protobuf.internal.containers.RepeatedScalarFieldContainer):
                temp = []
                temp.extend(value)
                value = temp
            m[a] = value
            
        return json.dumps(m)

    def handle_config(self, timestamp, data_obj):
        json_dict = self.handle_json_dictionary_from_proto(data_obj)
        self.add_to_events_queue([timestamp, "/muse/config", "s", [str(json_dict)], self.__config_id])

    def handle_version(self, timestamp, data_obj):
        json_dict = self.handle_json_dictionary_from_proto(data_obj)
        self.add_to_events_queue([timestamp, "/muse/version", "s", [str(json_dict)], self.__config_id])

    def handle_eeg(self, timestamp, data_obj):
        # Check if this is a 6 channel EEG message
        data_count = len(data_obj.values)
        osc_type = 'f'*data_count
        self.add_to_events_queue([timestamp, "/muse/eeg", osc_type, data_obj.values, self.__config_id])

    def handle_drlref(self, timestamp, data_obj):
        self.add_to_events_queue([timestamp, "/muse/drlref", "ff",
                            [data_obj.drl, data_obj.ref], self.__config_id])

    def handle_quantization(self, timestamp, data_obj):
        data_count = len(data_obj.values)
        osc_type = 'i'*data_count
        self.add_to_events_queue([timestamp, "/muse/eeg/quantization", osc_type,
                            data_obj.values, self.__config_id])

    def handle_acc(self, timestamp, data_obj):
        self.add_to_events_queue([timestamp, "/muse/acc", "fff",
                            [data_obj.acc1, data_obj.acc2, data_obj.acc3],
                            self.__config_id])

    def handle_batt(self, timestamp, data_obj):
        self.add_to_events_queue([timestamp, "/muse/batt", "iiii",
                              [data_obj.percent_remaining,
                               data_obj.battery_fuel_gauge_millivolts,
                               data_obj.battery_adc_millivolts,
                               data_obj.temperature_celsius], self.__config_id])

    def handle_annotation(self, timestamp, data_obj):
        if data_obj.event_data_format == Annotation.OSC:
            temp = data_obj.event_data.split(" ")
            path = temp[0]
            osc_types = temp[1]
            string_data = temp[2:2+len(osc_types)]
            data = []
            i = 0
            for osc_type in osc_types:
                if 'f' in osc_type:
                    data.append(float(string_data[i]))
                elif 'i' in osc_type:
                    data.append(int(string_data[i]))
                elif 'd' in osc_type:
                    data.append(float(string_data[i]))
                elif 's' in osc_type:
                    data.append(str(string_data[i]))
                i += 1
            self.add_to_events_queue([timestamp, path, osc_types, data, self.__config_id])
        else:
            event_format = ""
            if data_obj.event_data_format == Annotation.PLAIN_STRING:   
                event_format = "Plain String"
            elif data_obj.event_data_format == Annotation.JSON:
                event_format = "JSON"
            self.add_to_events_queue([timestamp, "/muse/annotation", "sssss", [data_obj.event_data, event_format, data_obj.event_type, data_obj.event_id, data_obj.parent_id], self.__config_id])
            
    def handle_dsp(self, timestamp, data_obj):
        data_count = len(data_obj.float_array)
        osc_type = 'f'*data_count
        self.add_to_events_queue([timestamp, "/muse/dsp/" + data_obj.type, osc_type, data_obj.float_array, self.__config_id])

    def handle_computing_device(self, timestamp, data_obj):
        json_dict = self.handle_json_dictionary_from_proto(data_obj)
        self.add_to_events_queue([timestamp, "/muse/device", "s", [str(json_dict)], self.__config_id])

    def handle_dropped_eeg(self, timestamp, data_obj):
        self.add_to_events_queue([timestamp, "/muse/eeg/dropped", "i", [data_obj.num], self.__config_id])

    def handle_dropped_acc(self, timestamp, data_obj):
        self.add_to_events_queue([timestamp, "/muse/acc/dropped", "i", [data_obj.num], self.__config_id])

    def add_to_events_queue(self, event):
        self.__timestamp = event[0]
        self.events_queue.put(event)
        self.added_to_events += 1

        while self.events_queue.qsize() >= 30000:
            time.sleep(0)
