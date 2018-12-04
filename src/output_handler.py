import liblo
import time
import utilities
import struct
import json
import re
import scipy.io
import numpy as np
import threading
from Muse_v2 import *
from Muse_v2 import _HEADLOCATIONS
from Muse_v2 import _EEGUNITS
from Muse_v2 import _ACCELEROMETERUNITS
import hdf5storage as h5
import collections

class OutputHandler(object):
    def __init__(self, queue):
        self.queue = queue
        self.listeners = []
        self.__start_time = 0
        self.__done = False
        self.__thread_lock = threading.Lock()

    def get_message(self):
        if self.__done:
            return 'done'
        else:
            return self.queue.get()

    def broadcast_message(self, msg):
        for listener in self.listeners:
            self.__thread_lock.acquire()
            if not self.__done:
                listener.receive_msg(msg)
            self.__thread_lock.release()

    def add_listener(self, listener):
        self.listeners.append(listener)

    def put_done_message(self):
        self.__done = True
        for listener in self.listeners:
            self.__thread_lock.acquire()
            listener.receive_msg('done')
            self.__thread_lock.release()

    @staticmethod
    def path_contains_filter(filters, type):
        if filters == None:
            return True
        else:
            for filter in filters:
                if re.search(filter, type):
                    return True
        return False

    def start(self, filters, verbose=False):
        for listener in self.listeners:
            listener.set_options(verbose, filters)
        done = False

        while not done:
            msg = self.get_message()
            if self.__start_time == 0:
                self.__start_time = msg[0]
            if ("done" in msg) or (self.__done == True):
                done = True
                utilities.DisplayPlayback.end()
            else:
                status = "Sending Data"
                utilities.DisplayPlayback.playback_time(msg[0] - self.__start_time, status)
            self.broadcast_message(msg)

class ScreenWriter(OutputHandler):
    def __init__(self):
        self.__paths = []

    def set_options(self, verbose, filters):
        self.__verbose = verbose
        self.__filters = filters

    def receive_msg(self, msg):
        if "done" in msg:
            return

        if not self.path_contains_filter(self.__filters, msg[1]):
            return

        dataset = ""
        if isinstance(msg[3], (float,int,unicode,str)):
            data = msg[3]
            if isinstance(data, str):
                dataset = dataset + " " + data
            elif isinstance(data, unicode):
                dataset = dataset + " " + data
            elif isinstance(data, int):
                dataset = dataset + " " + str(data)
            elif isinstance(data,float):
                dataset = dataset + " %.2f" % data
        else:
            for data in msg[3]:
                if isinstance(data, str):
                    dataset = dataset + " " + data
                elif isinstance(data, unicode):
                    dataset = dataset + " " + data
                elif isinstance(data, int):
                    dataset = dataset + " " + str(data)
                elif isinstance(data,float):
                    dataset = dataset + " %.2f" % data
        utilities.DisplayPlayback.print_msg(str(msg[0]) + " " + msg[1] + " " + str(msg[2]) + " " + dataset)

class MatlabWriter(OutputHandler):
    def __init__(self, out_file):
        # the most important part of dataset is now the first dict which contains the main struct, IXDATA
        self.__dataset = {}
        self.set_data_structure()
        self.__value = []
        self.__file_out = out_file
        self.received_data = 0
        self.data_written = 0
        self.files_written = 0
        self.__verbose = None
        self.__filters = None


    def set_data_structure(self, config = {}, device = {}):
        self.__dataset = {
            u'IXDATA': {
                u'sessionID': [],
                u'muse': [],
                u'raw': {
                    u'eeg': {
                        u'times': [],
                        u'data': [],
                        u'quantization_times': [],
                        u'quantization': [],
                        u'dropped_times': [],
                        u'dropped': []
                        },
                    u'acc': {
                        u'times': [],
                        u'data': [],
                        u'dropped_times': [],
                        u'dropped': []
                    },
                    u'battery': {
                        u'val': [],
                        u'times': []
                    },
                    u'drlref': {
                        u'times': [],
                        u'data': []
                    }
                },
                u'm_struct': {
                    u'm_names': [],
                    u'i_names': [],
                    u'm_times': [],
                    u'i_times': []
                },
                u'feat': [],
                u'class': []
            },
            u'config': {}, #config data
            u'device': {}, #computing device data
        }

    def set_options(self, verbose, filters):
        self.__verbose = verbose
        self.__filters = filters

    def write_array(self):

        # Check if there is anything to save
        if len(self.__dataset['config']) == 0:
            self.__dataset['config'] = [['config'], 'missing']
        if len(self.__dataset['device']) == 0:
            self.__dataset['device'] = [['device'], 'missing']

        file_name = self.__file_out
        if self.files_written:
            if '.mat' in self.__file_out[len(self.__file_out)-4:len(self.__file_out)]:
                file_name = self.__file_out[0:len(self.__file_out)-4] + '_' + str(self.files_written+1)
            else:
                file_name = self.__file_out + '_' + str(self.files_written+1)

        self.__dataset['IXDATA'] = self.convert_list_to_numpy_list(self.__dataset['IXDATA'])
        if 'elements' in self.__dataset:
            self.__dataset['elements'] = self.convert_list_to_numpy_list(self.__dataset['elements'])
        h5.write(self.__dataset, path='/', filename=file_name,  truncate_existing=True, store_python_metadata=True, matlab_compatible=True)

        self.files_written += 1

    def convert_list_to_numpy_list(self, dictionary):
        if not dictionary:
            return dictionary
        if isinstance(dictionary, dict):
            for key, value in dictionary.iteritems():
                if key in ['m_names', 'i_names']:
                    continue
                if isinstance(value, dict):
                    diction = self.convert_list_to_numpy_list(value)
                    dictionary[key] = diction
                elif isinstance(value, list):
                    dictionary[key] = np.array(value)
            return dictionary

    def handle_raw_data(self, osc_path, input_data):
            eeg_data_identifier = ["eeg/quantization", "eeg/dropped", "eeg"]
            acc_data_identifier = ["acc/dropped", "acc"]
            drlref_data_identifier = ["drlref"]
            battery_data_identifier = ["muse/batt"]

            if any(identifier in osc_path for identifier in eeg_data_identifier):
                type_key = "eeg"
                if "eeg/quantization" in osc_path:
                    time_key = "quantization_times"
                    data_key = "quantization"
                elif "eeg/dropped" in osc_path:
                    time_key = "dropped_times"
                    data_key = "dropped"
                elif "eeg" in osc_path:
                    time_key = "times"
                    data_key = "data"
            elif any(identifier in osc_path for identifier in acc_data_identifier):
                type_key = "acc"
                if "acc/dropped" in osc_path:
                    time_key = "dropped_times"
                    data_key = "dropped"
                elif "acc" in osc_path:
                    time_key = "times"
                    data_key = "data"
            elif any(identifier in osc_path for identifier in drlref_data_identifier):
                type_key = "drlref"
                time_key = "times"
                data_key = "data"
            elif any(identifier in osc_path for identifier in battery_data_identifier):
                type_key = "battery"
                time_key = "times"
                data_key = "val"

            self.__dataset['IXDATA']["raw"][type_key][time_key].append([input_data[0]])
            data = []
            for x in input_data[1:]:
                data.append(float(x))
            self.__dataset['IXDATA']["raw"][type_key][data_key].append(data)

    def handle_config_data(self, osc_path, input_data):
            old_format_offset = 6
            if "muse/config" in osc_path or "muse/version" in osc_path:
                key = "config"
                if "muse/config" in osc_path:
                    old_format_offset = 13
            elif "muse/device" in osc_path:
                key = "device"
            try:
                data = json.loads(input_data[1])
                for item in data:
                    if isinstance(data[item], unicode):
                        output_data = str(data[item])
                    else:
                        output_data = np.array(data[item])
                    self.__dataset[key][unicode(item)] = [np.array(input_data[0]), output_data]
            except:
                datatype = osc_path[old_format_offset:]
                self.__dataset[key][unicode(datatype)] = [[input_data[0]], input_data[1]]

    def create_dict_based_on_path(self, dictionary, path_list, dataset):
        if len(path_list) == 1:
            dictionary.setdefault(unicode(path_list[0]), []).append(dataset)
            return dictionary
        else:
            dictionary[unicode(path_list[0])] = self.create_dict_based_on_path(dictionary.setdefault(unicode(path_list[0]), {}), path_list[1:], dataset)
            return dictionary

    def receive_msg(self, msg):
        raw_data_identifier = ["eeg/quantization", "eeg/dropped", "eeg", "acc/dropped", "acc", "drlref", "muse/batt"]
        config_identifier = ["muse/config", "muse/version", "muse/device"]
        if "done" in msg:
            self.write_array()
            return

        if not self.path_contains_filter(self.__filters, msg[1]):
            self.received_data += 1
            self.data_written += 1
            return

        temp = []
        temp.append(msg[0])
        i = 1
        for x in msg[3]:
            temp.append(x)
            i = i + 1
        if ('i' in msg[2]) or ('f' in msg[2]) or ('d' in msg[2]) or ('s' in msg[2]):
            if any(identifier in msg[1] for identifier in raw_data_identifier):
                self.handle_raw_data(msg[1], temp)
            elif any(identifier in msg[1] for identifier in config_identifier):
                self.handle_config_data(msg[1], temp)
            elif "muse/annotation" in msg[1]:
                if (re.search('Start$', temp[1]) or re.search('BEGIN$', temp[1])) and not ('Click' in temp[1]) and not ('Session' in temp[1]):
                    self.__dataset["IXDATA"]["m_struct"]["m_names"].append([str(temp[1][8:len(temp[1])-6])])
                    self.__dataset["IXDATA"]["m_struct"]["m_times"].append([temp[0], 0])
                elif re.search('Stop$', temp[1]) or re.search("Done$", temp[1]) or re.search("END$", temp[1]):
                    self.__dataset["IXDATA"]["m_struct"]["m_times"].append([temp[0], 1])
                elif len(temp) > 3:
                    if 'instance' in temp[3]:
                        self.__dataset["IXDATA"]["m_struct"]["i_names"].append([str(temp[1][1:])])
                        self.__dataset["IXDATA"]["m_struct"]["i_times"].append([temp[0]])
                    elif 'begin' in temp[3]:
                        self.__dataset["IXDATA"]["m_struct"]["m_names"].append([str(temp[1][8:])])
                        self.__dataset["IXDATA"]["m_struct"]["m_times"].append([temp[0], 0])
                    elif 'end' in temp[3]:
                        self.__dataset["IXDATA"]["m_struct"]["m_times"].append([temp[0], 1])
                    else:
                        self.__dataset["IXDATA"]["m_struct"]["i_names"].append([unicode(temp[1])])
                        self.__dataset["IXDATA"]["m_struct"]["i_times"].append([temp[0]])
                else:
                    self.__dataset["IXDATA"]["m_struct"]["i_names"].append([str(temp[1])])
                    self.__dataset["IXDATA"]["m_struct"]["i_times"].append([temp[0]])
            elif "/muse/elements" in msg[1]:
                msg[1] = msg[1].replace('-', '_')
                name = msg[1][15:].replace('/', '_')
                self.__dataset.setdefault(u'elements', {}).setdefault(unicode(name), []).append(temp)
        else:
            if self.__verbose:
                print "Unknown Data ", msg[1], " ", msg[2], " ", msg[3]

        self.received_data += 1
        self.data_written += 1
        if self.received_data > 36000*30: #Approximately 1 minutes at 500Hz * 30 for 30 minutes files
            self.write_array()
            self.received_data = 0



"""class LSLMessageWriter(object):
    def __init__(self, address):
        self.__address = address

    def receive_msg(self, msg):
        if "done" in msg:
            return

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


        if len(str(msg[3])) < 2000:

            liblo.send(self.__address, msg[1], *msg[3])
        else:
            print len(str(msg[3]))
"""


class OSCMessageWriter(OutputHandler):
    def __init__(self, address):
        self.__address = liblo.Address(address)

    def set_options(self, verbose, filters):
        self.__verbose = verbose
        self.__filters = filters

    def receive_msg(self, msg):
        if "done" in msg:
            return

        if not self.path_contains_filter(self.__filters, msg[1]):
            return

        if len(str(msg[3])) < 3000:
            try:
                liblo.send(self.__address, msg[1], *msg[3])
            except:
                status = "Connection Failed, retrying in 1 second."
                utilities.DisplayPlayback.post_connection_issue(status)
                time.sleep(1)
                self.receive_msg(msg)
        else:
            error_msg = 'A Message is too long for OSC Send: ' + str(len(str(msg[3]))) + " bytes long         "
            utilities.DisplayPlayback.playback_error(error_msg)

class CSVFileWriter(OutputHandler):
    def __init__(self, output_path):
        self.__done_status = False
        try:
            self.file_handle = open(output_path, 'w')
        except:
            print "Error: Unable to open a file at %s" % output_path
            exit()

    def set_options(self, verbose, filters):
        self.__verbose = verbose
        self.__filters = filters


    def receive_msg(self, msg):
        if "done" in msg:
            self.__done_status = True
            self.close_file()
            return

        if not self.path_contains_filter(self.__filters, msg[1]):
            return

        timestamp = msg[0]
        path = msg[1]
        type = msg[2]
        if "s" in type:
            data = ", ".join("'" + str(x.encode('utf-8')).rstrip() +"'" for x in msg[3])
        else:
            data = ", ".join(str(x) for x in msg[3])

        msg_to_write = ("%.6f" % timestamp)  +  ", "  + path + ", " + data + "\n"

        if (self.file_handle is not None) and (self.__done_status == False):
            self.file_handle.write(msg_to_write)
        elif self.__done_status == True:
            print "Forced stop: Writing complete"
        else:
            print "Error: No file handle"

    def close_file(self):
        self.file_handle.close()

class OSCFileWriter(OutputHandler):
    def __init__(self, output_path):
        self.__done_status = False
        try:
            self.file_handle = open(output_path, 'w')
        except:
            print "Error: Unable to open a file at %s" % output_path
            exit()

    def set_options(self, verbose, filters):
        self.__verbose = verbose
        self.__filters = filters

    def receive_msg(self, msg):
        if "done" in msg:
            self.__done_status = True
            self.close_file()
            return

        if not self.path_contains_filter(self.__filters, msg[1]):
            return

        timestamp = msg[0]
        path = msg[1]
        types = msg[2]
        position = 0
        data = ''
        for type in types:
            if "s" in type:
                no_return = msg[3][position].rstrip()
                data += "'" + no_return + "'"
#            elif 'f' in type:
#                data += " " + "%.6f" % float(msg[3][position])
            else:
                data += " " + str(msg[3][position])
            position += 1

        msg_to_write = ("%f" % timestamp)  +  " "  + path + " " + types + " " + data + "\n"

        if (self.file_handle is not None) and (self.__done_status == False):
            self.file_handle.write(msg_to_write.encode('utf-8'))
        elif self.__done_status == True:
            print "Forced stop: Writing complete"
        else:
            print "Error: No file handle"

    def close_file(self):
        self.file_handle.close()


class ProtoBufFileWriter(OutputHandler):
    def __init__(self, output_path):
        try:
            self.file_handle = open(output_path, 'wb')
        except:
            print "Error: Unable to open a file at %s" % output_path
            exit()
        self.muse_data_collection = MuseDataCollection()
        self.config_data = None
        self.config = None
        self.seen_config_first_entry = False
        self.all_config_entry_so_far = []

        self.attr_does_not_exist = ["error_stat_enabled"]
        self.received_data = 0
        self.data_sent = 0

    def set_options(self, verbose, filters):
        self.__verbose = verbose
        self.__filters = filters

    def receive_msg(self, msg):
        if "done" in msg:
            self.write_to_file_and_close()
            return

        if not self.path_contains_filter(self.__filters, msg[1]):
            return

        timestamp = msg[0]
        path = msg[1]
        osc_types = msg[2]
        data = msg[3]
        config_id = msg[4]

        muse_data = self.muse_data_collection.collection.add()
        muse_data.timestamp = timestamp
        muse_data.config_id = config_id

        if "/muse/config" in path:
            muse_data.datatype = MuseData.CONFIG
            configDictionary = json.loads(data[0])

            muse_config_data = muse_data.Extensions[MuseConfig.museData]
            for config_key in configDictionary:
                value = configDictionary[config_key]
                if 'accelerometer_data_enabled' in config_key:
                    print config_key
                elif 'error_stat_enabled' in config_key:
                    print config_key
                    setattr(muse_config_data, 'error_data_enabled', configDictionary[config_key])
                elif isinstance(value, list) and (muse_config_data.eeg_locations == []):
                    for y in value:
                        muse_config_data.eeg_locations.append(y)
                elif isinstance(value, unicode):
                    values = value.split()
                    if(len(values) > 1):
                        if(muse_config_data.eeg_locations == []):
                            for loc in values:
                                muse_config_data.eeg_locations.append(_HEADLOCATIONS.values_by_name[loc].number)
                        setattr(muse_config_data, config_key, str(configDictionary[config_key]))
                    elif configDictionary[config_key] in _EEGUNITS.values_by_name.keys():
                        setattr(muse_config_data, config_key, _EEGUNITS.values_by_name[configDictionary[config_key]].number)
                    elif configDictionary[config_key] in _ACCELEROMETERUNITS.values_by_name.keys():
                        setattr(muse_config_data, config_key, _ACCELEROMETERUNITS.values_by_name[configDictionary[config_key]].number)
                    elif configDictionary[config_key] in utilities.units_dictionary:
                        setattr(muse_config_data, config_key, utilities.units_dictionary[configDictionary[config_key]])
                    else:
                        setattr(muse_config_data, config_key, str(configDictionary[config_key]))
                else:
                    try:
                        setattr(muse_config_data, config_key, configDictionary[config_key])
                    except:
                        if self.__verbose:
                            print 'Attribute does not exist in Muse Config File Format: ' + config_key
        elif "/muse/device" in path:
            muse_data.datatype = MuseData.COMPUTING_DEVICE
            deviceDictionary = json.loads(data[0])

            muse_device_data = muse_data.Extensions[ComputingDevice.museData]
            for device_key in deviceDictionary:
                value = deviceDictionary[device_key]
                if isinstance(value, unicode):
                    setattr(muse_device_data, device_key, str(deviceDictionary[device_key]))
                else:
                    try:
                        setattr(muse_device_data, device_key, deviceDictionary[device_key])
                    except:
                        if self.__verbose:
                            print 'Attribute does not exist in Muse Device File Format: ' + device_key


        elif "/muse/eeg/quantization" in path:
            muse_data.datatype= MuseData.QUANT
            muse_quant_data = muse_data.Extensions[MuseQuantization.museData]
            for x in data:
                muse_quant_data.values.append(int(x))

        elif "/muse/eeg/dropped" in path:
            muse_data.datatype= MuseData.EEG_DROPPED
            muse_eeg_dropped_data = muse_data.Extensions[EEG_DroppedSamples.museData]
            muse_eeg_dropped_data.num = data[0]

        elif "/muse/eeg" in path:
            muse_data.datatype= MuseData.EEG
            muse_eeg_data = muse_data.Extensions[EEG.museData]

            for value in data:
                muse_eeg_data.values.append(float(value))

        elif "/muse/acc/dropped" in path:
            muse_data.datatype= MuseData.ACC_DROPPED
            muse_acc_dropped_data = muse_data.Extensions[ACC_DroppedSamples.museData]
            muse_acc_dropped_data.num = data[0]


        elif "/muse/acc" in path:
            muse_data.datatype= MuseData.ACCEL
            muse_acc_data = muse_data.Extensions[Accelerometer.museData]
            muse_acc_data.acc1 = float(data[0])
            muse_acc_data.acc2 = float(data[1])
            muse_acc_data.acc3 = float(data[2])

        elif "/muse/batt" in path:
            muse_data.datatype= MuseData.BATTERY
            muse_batt_data = muse_data.Extensions[Battery.museData]
            muse_batt_data.percent_remaining = data[0]
            muse_batt_data.battery_fuel_gauge_millivolts = data[1]
            muse_batt_data.battery_adc_millivolts = data[2]
            muse_batt_data.temperature_celsius = data[3]

        elif "/muse/drlref" in path:
            muse_data.datatype= MuseData.EEG
            muse_eeg_data = muse_data.Extensions[EEG.museData]
            muse_eeg_data.drl = float(data[0])
            muse_eeg_data.ref = float(data[1])

        elif "/muse/version" in path:
            muse_data.datatype= MuseData.VERSION
            versionDictionary = json.loads(data[0])
            #When more than one data is present, a timestamp is appended, may replace timestamp
            #if len(data) > 1:
            #    print len(data)
            #    print '%.6f' % float(str(data[1]) + '.' + str(data[2]))

            muse_version_data = muse_data.Extensions[MuseVersion.museData]
            for version_key in versionDictionary:
                if 'firmware_version' in version_key:
                    print version_key
                    setattr(muse_version_data, 'firmware_headset_version', str(versionDictionary[version_key]))
                else:
                    try:
                        setattr(muse_version_data, version_key, str(versionDictionary[version_key]))
                    except:
                        if self.__verbose:
                            print 'Attribute does not exist in Muse Version File Format: ' + version_key


        elif "/muse/annotation" in path:
            muse_data.datatype= MuseData.ANNOTATION
            muse_anno_data = muse_data.Extensions[Annotation.museData]
            muse_anno_data.event_data = data[0]
            if data[1] == "Plain String":
                muse_anno_data.event_data_format = int(Annotation.PLAIN_STRING)
            elif data[1] == "JSON":
                muse_anno_data.event_data_format = int(Annotation.JSON)
            muse_anno_data.event_type = data[2]
            muse_anno_data.event_id = data[3]
            muse_anno_data.parent_id = data[4]
        elif "/muse/dsp" in path:
            muse_data.datatype=MuseData.DSP
            muse_dsp_data = muse_data.Extensions[DSP.museData]
            muse_dsp_data.type = path[10:]
            for value in data:
                muse_dsp_data.float_array.append(float(value))

        else:
            muse_data.datatype = MuseData.ANNOTATION
            muse_anno_data = muse_data.Extensions[Annotation.museData]
            data_msg = ""
            data_msg += path + " "
            data_msg += osc_types + " "
            i = 0
            for osc_type in osc_types:
                data_msg += str(data[i]) + " "
                i += 1
            muse_anno_data.event_data = data_msg
            muse_anno_data.event_data_format = int(Annotation.OSC)
            muse_anno_data.event_type = ''
            muse_anno_data.event_id = ''
            muse_anno_data.parent_id = ''
            if self.__verbose:
                print 'Unkwown type'
                print path
                print data

        self.received_data += 1
        self.data_sent += 1
        if self.received_data > 3000:
            self.write_to_file()
            self.received_data = 0

    def write_to_file(self):
        data_bytes = self.muse_data_collection.SerializeToString()
        self.file_handle.write(struct.pack("i", len(data_bytes)))
        self.file_handle.write(struct.pack("h", 2))
        self.file_handle.write(data_bytes)
        self.muse_data_collection = MuseDataCollection()

    def write_to_file_and_close(self):
        data_bytes = self.muse_data_collection.SerializeToString()
        self.file_handle.write(struct.pack("i", len(data_bytes)))
        self.file_handle.write(struct.pack("h", 2))
        self.file_handle.write(data_bytes)
        self.file_handle.close()
