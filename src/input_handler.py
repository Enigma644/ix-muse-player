import liblo
import sys
import time
import shlex
import utilities
import threading
from liblo_error_explainer import LibloErrorExplainer
from proto_reader_v1 import *
from proto_reader_v2 import *


class InputHandler(object):
    def __init__(self, queue):
        self.queue = queue
        self.gap_size = 0
        self.last_timestamp = 0
        self.delta = 0
        self.input_queue = Queue.Queue()
        self.done = False

    def put_message(self, msg):
        self.queue.put(msg)

    def put_done_message(self):
        self.done = True
        self.put_message(["done"])

    def start_file(self, events, as_fast_as_possible=False, jump_data_gaps=False):
        if len(events) == 0:
            return

        # (1) get the current time
        if not self.delta:
            self.delta = time.time() - events[0][0]
        self.last_timestamp = self.delta
        if not utilities.DisplayPlayback.start_time:
            start_time = time.time()
            utilities.DisplayPlayback.set_start_time(start_time)

        # (2) Loop over messages
        for m in events:
            if 'done' in m:
                self.put_done_message()
                return

            if not as_fast_as_possible:
                # (4) Wait until the time is right. and send.
                time_to_wait = m[0] + self.delta - time.time() - utilities.DisplayPlayback.gap_time
                self.gap_size = m[0] - self.last_timestamp
                self.last_timestamp = m[0]
                if (time_to_wait > 1) and jump_data_gaps:
                    utilities.DisplayPlayback.gap_time = time_to_wait + utilities.DisplayPlayback.gap_time
                    time_to_wait = 1
                if time_to_wait > 0:
                    time.sleep(time_to_wait)

            self.put_message(m)

class OSCListener(InputHandler):
    def __init__(self, queue, address):
        super(OSCListener, self).__init__(queue)
        port_options = address.split(':')
        self.port_type = liblo.TCP
        if len(port_options) == 1:
            if port_options[0].isdigit():
                self.port = address
            else:
                if port_options[0].lower() == 'udp':
                    self.port_type = liblo.UDP
                else:
                    self.port_type = liblo.TCP
                self.port = 5000

        else:
            if port_options[0].lower() == 'udp':
                self.port_type = liblo.UDP
            self.port = port_options[1]

    def receive_message(self, path, arg, types, src):
        timestamp = time.time()

        msg_to_queue = [timestamp, path, types, arg, 0]
        self.put_message(msg_to_queue)

    def start(self, as_fast_as_possible=False, jump_data_gaps=False):
        try:
            server = liblo.Server(self.port, self.port_type)
            server.add_method(None, None, self.receive_message)
            while not self.done:
                server.recv(1)
        except liblo.ServerError, err:
            print >>sys.stderr, str(err)
            explanation = LibloErrorExplainer(err).explanation()
            if explanation:
                print >>sys.stderr, explanation
            sys.exit(1)

class MuseProtoBufFileReader(InputHandler):
    def __init__(self, queue):
        InputHandler.__init__(self, queue)
        self.protobuf_reader = []
        self.parsing_threads = []
        self.__events = []
        self.added_to_queue_events = 0
        self.events_added_by_threads = 0

    # Parses multiple input files, sortes by time and calls the handler functions.
    def parse_files(self, file_names, verbose=True, as_fast_as_possible=False, jump_data_gaps=False):
        file_stream = []
        for file_name in file_names:
            if verbose:
                print "Parsing file", file_name
            try:
                file_stream.append(open(file_name, "rb"))
            except:
                print "File not found: " + file_name
                self.put_done_message()
                exit()

        self.__parse_head(file_stream, verbose, as_fast_as_possible, jump_data_gaps)

    def __parse_head(self, in_streams, verbose=True, as_fast_as_possible=False, jump_data_gaps=False):
        for in_stream in in_streams:

            # (1) Read the message header
            header_bin = in_stream.read(4)
            # check for EOF
            if len(header_bin) == 0:
                print "Zero Sized Muse File"
                exit()

            header = struct.unpack("<i", header_bin)
            msg_length = header[0]
            msg_type = in_stream.read(2)
            msg_type = struct.unpack("<h", msg_type)
            msg_type = msg_type[0]
            in_stream.seek(0,0)
            if verbose:
                print 'Muse File version #' + str(msg_type)
            if msg_type == 1:
                # set reader to version 1
                self.protobuf_reader.append(MuseProtoBufReaderV1(verbose))

            elif msg_type == 2:
                # set reader to version 2
                self.protobuf_reader.append(MuseProtoBufReaderV2(verbose))


            parse_thread = threading.Thread(target=self.protobuf_reader[in_streams.index(in_stream)].parse, args=[in_stream])
            parse_thread.daemon = True
            parse_thread.start()
            self.parsing_threads.append(parse_thread)

        queueing_thread = threading.Thread(target=self.craft_input_queue)
        queueing_thread.daemon = True
        queueing_thread.start()

        data_remains = True
        while data_remains:
            while queueing_thread.is_alive() and self.input_queue.empty():
                time.sleep(0)

            self.start_queue(as_fast_as_possible, jump_data_gaps)

            if len(self.protobuf_reader) == 0:
                queueing_thread.join()
                data_remains = False

    def start_queue(self, as_fast_as_possible, jump_data_gaps):
        if self.input_queue.empty():
            return

        # (1) get the current time
        if not self.delta:
            self.delta = time.time() - self.input_queue.queue[0][0]
        self.last_timestamp = self.delta
        if not utilities.DisplayPlayback.start_time:
            start_time = time.time()
            utilities.DisplayPlayback.set_start_time(start_time)

        # (2) Loop over messages
        while not self.input_queue.empty():
            event = self.input_queue.get()
            if 'done' in event:
                self.put_done_message()
                return
            if not as_fast_as_possible:
                # (4) Wait until the time is right. and send.
                time_to_wait = event[0] + self.delta - time.time() - utilities.DisplayPlayback.gap_time
                self.gap_size = event[0] - self.last_timestamp
                self.last_timestamp = event[0]
                if (time_to_wait > 1) and jump_data_gaps:
                    utilities.DisplayPlayback.gap_time = time_to_wait + utilities.DisplayPlayback.gap_time
                    time_to_wait = 1
                if time_to_wait > 0:
                    time.sleep(time_to_wait)

            self.put_message(event)

    def craft_input_queue(self):
        while len(self.protobuf_reader) != 0:
            queue_status = 'data available'
            for parser in self.protobuf_reader:
                if parser.events_queue.empty():
                    queue_status = 'empty'
                    while parser.events_queue.empty():
                        time.sleep(0)

            if 'data available' in queue_status:
                earliest_index = 0
                earliest_time = [time.time()]
                for parser in self.protobuf_reader:
                    if parser.events_queue.queue[0][0] <= earliest_time:
                        earliest_time = parser.events_queue.queue[0][0]
                        earliest_index = self.protobuf_reader.index(parser)

                earliest_event = self.protobuf_reader[earliest_index].events_queue.get()
                if 'done' in earliest_event:
                    if len(self.protobuf_reader) == 1:
                        self.input_queue.put([earliest_time + 0.1, 'done'])
                    del self.protobuf_reader[earliest_index]
                    del self.parsing_threads[earliest_index]

                else:
                    self.added_to_queue_events += 1
                    self.input_queue.put(earliest_event)

            while (self.input_queue.qsize() >= 30000) and (len(self.protobuf_reader) != 0):
                time.sleep(0)


    # Replays Musefile messages. Optionally as fast as possible, optionally jumping data gaps.
    def start(self, as_fast_as_possible=False, jump_data_gaps=False):
        self.start_file(self.__events, as_fast_as_possible, jump_data_gaps)

class MuseOSCFileReader(InputHandler):
    def __init__(self, queue):
        InputHandler.__init__(self, queue)
        self.__events = []
        self.oscfile_reader = []
        self.parsing_threads = []


    def parse_files(self, file_names, verbose=True, as_fast_as_possible=False, jump_data_gaps=False):
        file_stream = []
        for file_path in file_names:
            if verbose:
                print "Parsing file", file_path
            try:
                file_stream.append(open(file_path, "rb"))
            except:
                print "File not found: " + file_path
                self.put_done_message()
                exit()

        self.__parse_head(file_stream, verbose, as_fast_as_possible, jump_data_gaps)

    def start_queue(self, as_fast_as_possible, jump_data_gaps):
         if self.input_queue.empty():
             return

         # (1) get the current time
         if not self.delta:
             self.delta = time.time() - self.input_queue.queue[0][0]
         self.last_timestamp = self.delta
         if not utilities.DisplayPlayback.start_time:
             start_time = time.time()
             utilities.DisplayPlayback.set_start_time(start_time)

         # (2) Loop over messages
         while not self.input_queue.empty():
             event = self.input_queue.get()
             if 'done' in event:
                 self.put_done_message()
                 return
             if not as_fast_as_possible:
                 # (4) Wait until the time is right. and send.
                 time_to_wait = event[0] + self.delta - time.time() - utilities.DisplayPlayback.gap_time
                 self.gap_size = event[0] - self.last_timestamp
                 self.last_timestamp = event[0]
                 if (time_to_wait > 1) and jump_data_gaps:
                     utilities.DisplayPlayback.gap_time = time_to_wait + utilities.DisplayPlayback.gap_time
                     time_to_wait = 1
                 if time_to_wait > 0:
                     time.sleep(time_to_wait)

             self.put_message(event)
         self.put_done_message()

    # Replays OSC messages. Optionally as fast as possible.
    def start(self, as_fast_as_possible=False, jump_data_gaps=False):
        self.start_file(self.__events, as_fast_as_possible, jump_data_gaps)

    def __parse_head(self, in_streams, verbose=True, as_fast_as_possible=False, jump_data_gaps=False):
        for in_stream in in_streams:

            self.oscfile_reader.append(oscFileReader(verbose))

            parse_thread = threading.Thread(target=self.oscfile_reader[in_streams.index(in_stream)].read_file, args=[in_stream])
            parse_thread.daemon = True
            parse_thread.start()
            self.parsing_threads.append(parse_thread)

        queueing_thread = threading.Thread(target=self.craft_input_queue)
        queueing_thread.daemon = True
        queueing_thread.start()

        data_remains = True
        while data_remains:
            while queueing_thread.is_alive() and self.input_queue.empty():
                time.sleep(0)

            self.start_queue(as_fast_as_possible, jump_data_gaps)

            if len(self.oscfile_reader) == 0:
                queueing_thread.join()
                data_remains = False

    def start_queue(self, as_fast_as_possible, jump_data_gaps):
        if self.input_queue.empty():
            return

        # (1) get the current time
        if not self.delta:
            self.delta = time.time() - self.input_queue.queue[0][0]
        self.last_timestamp = self.delta
        if not utilities.DisplayPlayback.start_time:
            start_time = time.time()
            utilities.DisplayPlayback.set_start_time(start_time)

        # (2) Loop over messages
        while not self.input_queue.empty():
            event = self.input_queue.get()
            if 'done' in event:
                self.put_done_message()
                return
            if not as_fast_as_possible:
                # (4) Wait until the time is right. and send.
                time_to_wait = event[0] + self.delta - time.time() - utilities.DisplayPlayback.gap_time
                self.gap_size = event[0] - self.last_timestamp
                self.last_timestamp = event[0]
                if (time_to_wait > 1) and jump_data_gaps:
                    utilities.DisplayPlayback.gap_time = time_to_wait + utilities.DisplayPlayback.gap_time
                    time_to_wait = 1
                if time_to_wait > 0:
                    time.sleep(time_to_wait)

            self.put_message(event)

    def craft_input_queue(self):
        while len(self.oscfile_reader) != 0:
            queue_status = 'data available'
            for parser in self.oscfile_reader:
                if parser.events_queue.empty():
                    queue_status = 'empty'
                    while parser.events_queue.empty():
                        time.sleep(0)

            if 'data available' in queue_status:
                earliest_index = 0
                earliest_time = [time.time()]
                for parser in self.oscfile_reader:
                    if parser.events_queue.queue[0][0] <= earliest_time:
                        earliest_time = parser.events_queue.queue[0][0]
                        earliest_index = self.oscfile_reader.index(parser)

                earliest_event = self.oscfile_reader[earliest_index].events_queue.get()
                if 'done' in earliest_event:
                    if len(self.oscfile_reader) == 1:
                        self.input_queue.put([earliest_time + 0.1, 'done'])
                    del self.oscfile_reader[earliest_index]
                    del self.parsing_threads[earliest_index]

                else:
                    #self.added_to_queue_events += 1
                    self.input_queue.put(earliest_event)

            while (self.input_queue.qsize() >= 30000) and (len(self.protobuf_reader) != 0):
                time.sleep(0)


    # Replays Musefile messages. Optionally as fast as possible, optionally jumping data gaps.
    def start(self, as_fast_as_possible=False, jump_data_gaps=False):
        self.start_file(self.__events, as_fast_as_possible, jump_data_gaps)

class oscFileReader(object):

    def __init__(self, verbose=False):
            self.events_queue = Queue.Queue()
            self.last_timestamp = 0

    def read_file(self, file, verbose=False):

        line = file.readline()
        while line:
            newLine = self.parse_line(line)
            if newLine != []:
                self.add_to_events_queue(newLine)
            line = file.readline()
        self.add_done()

    def parse_line(self, line):
        info = shlex.split(line.strip())
        if(len(info) > 0):
            data_array = []
            data_array.append(float(info[0]))
            if('Marker' in info[1]):
                data_array.append('muse/annotation')
                data_array.append('s')
                data_array.append([info[1]])
                self.last_timestamp = float(info[1])
                data_array.append(0) #config id placement, need to fix in the future
                return data_array
            else:
                data_array.append(info[1])
                typeListComplete = ''
                data_to_store = []


                typeList = info[2]
                typeListComplete = typeListComplete + typeList
                dataLength = len(info[3:])
                dataCount = 3
                while dataLength > 0:
                    for type in typeList:
                        if 'f' in type:
                            data = float(info[dataCount])
                        elif 'i' in type:
                            data = int(info[dataCount])
                        elif 'd' in type:
                            data = float(info[dataCount])
                        elif 's' in type:
                            rawline = line.split("'")
                            data = rawline[dataCount-2]
                        dataCount = dataCount + 1
                        dataLength = dataLength - 1
                        data_to_store.append(data)
                    if dataLength > 0:
                        typeList = info[dataCount]
                        typeListComplete = typeListComplete + typeList
                        dataCount = dataCount + 1
                        dataLength = dataLength - 1

                data_array.append(typeListComplete)
                data_array.append(data_to_store)
                data_array.append(0)
                return data_array
        return []

    def add_done(self):
        self.add_to_events_queue([self.last_timestamp + 0.001, 'done'])

    def add_to_events_queue(self, event):
        self.last_timestamp = event[0]
        self.events_queue.put(event)

        while self.events_queue.qsize() >= 30000:
            time.sleep(0)
