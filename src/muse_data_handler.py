import struct
import sys
import Muse_V1 as Muse_pb1
import Muse_V2 as Muse_pb2


# Parses serialized binary data stream and calls corresponding handler function based on data type
class MuseProtoBufDataHandler(object):

    # Parses a single file and calls the handler functions. The order is preserved.
    def parse_file(self, file_name):
        file_stream = open(file_name, "rb")
        objects = []
        mtype = []
        self.__parse(file_stream, objects.extend, mtype)
        for obj in objects:
            self.__handle_data(obj)

    # Parses multiple input files, sortes by time and calls the handler functions.
    def parse_files(self, file_names, verbose=False):
        objects = []
        mtype = []
        for file_name in file_names:
            if verbose:
                print "Parsing file", file_name

            file_stream = open(file_name, "rb")
            self.__parse(file_stream, objects.extend, mtype)

        objects.sort(key=lambda md: md.timestamp)
        for obj in objects:
            self.__handle_data(obj, mtype)

    @staticmethod
    def __parse(in_stream, callback, mtype):
        while True:
            # (1) Read the message header
            header_bin = in_stream.read(4)
            # check for EOF
            if len(header_bin) == 0:
                break

            header = struct.unpack("<i", header_bin)
            msg_length = header[0]
            msg_type = in_stream.read(2)
            mtype.append(msg_type)            

            if msg_type == 1:
                # (2) Read and parse the message
                msg_bin = in_stream.read(msg_length)
                muse_data_collection = Muse_pb1.MuseDataCollection()
                muse_data_collection.ParseFromString(msg_bin)

                # (3) Process this chunk of data
                callback(muse_data_collection.collection)
            elif msg_type == 2:
                # (2) Read and parse the message
                msg_bin = in_stream.read(msg_length)
                muse_data_collection = Muse_pb2.MuseDataCollection()
                muse_data_collection.ParseFromString(msg_bin)

                # (3) Process this chunk of data
                callback(muse_data_collection.collection)

    # dispatch based on data type
    def __handle_data(self, md, mtype):
        # Version 2 response
        # Configuration data
        if md.datatype == Muse_pb2.MuseData.CONFIG:
            data_obj = md.Extensions[Muse_pb.MuseConfig.museData]
            self.handle_config(md.timestamp, data_obj)

        # Version
        if md.datatype == Muse_pb2.MuseData.VERSION:
            data_obj = md.Extensions[Muse_pb.MuseVersion.museData]
            self.handle_version(md.timestamp, data_obj)

        # EEG samples
        if md.datatype == Muse_pb2.MuseData.EEG:
            data_obj = md.Extensions[Muse_pb.MuseEEG.museData]
            # Check if this is a DRL/REF message
            if data_obj.HasField("drl"):
                self.handle_drlref(md.timestamp, data_obj)
            else:
                self.handle_eeg(md.timestamp, data_obj)

        # Quantization data
        if md.datatype == Muse_pb2.MuseData.QUANT:
            data_obj = md.Extensions[Muse_pb.MuseQuantization.museData]
            self.handle_quantization(md.timestamp, data_obj)

        # Accelerometer
        if md.datatype == Muse_pb2.MuseData.ACCEL:
            data_obj = md.Extensions[Muse_pb.MuseAccelerometer.museData]
            self.handle_acc(md.timestamp, data_obj)

        # Battery
        if md.datatype == Muse_pb2.MuseData.BATTERY:
            data_obj = md.Extensions[Muse_pb.MuseBattery.museData]
            self.handle_batt(md.timestamp, data_obj)

        # Annotations
        if md.datatype == Muse_pb2.MuseData.ANNOTATION:
            data_obj = md.Extensions[Muse_pb.MuseAnnotation.museData]
            self.handle_annotation(md.timestamp, data_obj)

        # Version 1 Response
        # Configuration data
        if md.datatype == Muse_pb1.MuseData.CONFIG:
            data_obj = md.Extensions[Muse_pb.MuseConfig.museData]
            self.handle_config(md.timestamp, data_obj)

        # Version
        if md.datatype == Muse_pb1.MuseData.VERSION:
            data_obj = md.Extensions[Muse_pb.MuseVersion.museData]
            self.handle_version(md.timestamp, data_obj)

        # EEG samples
        if md.datatype == Muse_pb1.MuseData.EEG:
            data_obj = md.Extensions[Muse_pb.MuseEEG.museData]
            # Check if this is a DRL/REF message
            if data_obj.HasField("drl"):
                self.handle_drlref(md.timestamp, data_obj)
            else:
                self.handle_eeg(md.timestamp, data_obj)

        # Quantization data
        if md.datatype == Muse_pb1.MuseData.QUANT:
            data_obj = md.Extensions[Muse_pb.MuseQuantization.museData]
            self.handle_quantization(md.timestamp, data_obj)

        # Accelerometer
        if md.datatype == Muse_pb1.MuseData.ACCEL:
            data_obj = md.Extensions[Muse_pb.MuseAccelerometer.museData]
            self.handle_acc(md.timestamp, data_obj)

        # Battery
        if md.datatype == Muse_pb1.MuseData.BATTERY:
            data_obj = md.Extensions[Muse_pb.MuseBattery.museData]
            self.handle_batt(md.timestamp, data_obj)

        # Annotations
        if md.datatype == Muse_pb1.MuseData.ANNOTATION:
            data_obj = md.Extensions[Muse_pb.MuseAnnotation.museData]
            self.handle_annotation(md.timestamp, data_obj)

 
    # Version 2 Handlers
    def handle_config_2(self, timestamp, data_obj):
        pass

    def handle_version_2(self, timestamp, data_obj):
        pass

    def handle_eeg_2(self, timestamp, data_obj):
        pass

    def handle_drlref_2(self, timestamp, data_obj):
        pass

    def handle_quantization_2(self, timestamp, data_obj):
        pass

    def handle_acc_2(self, timestamp, data_obj):
        pass

    def handle_batt_2(self, timestamp, data_obj):
        pass

    def handle_annotation_2(self, timestamp, data_obj):
        pass 
    
    # Version 1 Handlers 
    def handle_config(self, timestamp, data_obj):
        pass

    def handle_version(self, timestamp, data_obj):
        pass

    def handle_eeg(self, timestamp, data_obj):
        pass

    def handle_drlref(self, timestamp, data_obj):
        pass

    def handle_quantization(self, timestamp, data_obj):
        pass

    def handle_acc(self, timestamp, data_obj):
        pass

    def handle_batt(self, timestamp, data_obj):
        pass

    def handle_annotation(self, timestamp, data_obj):
        pass
