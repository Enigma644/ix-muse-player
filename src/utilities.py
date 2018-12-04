import sys
import time
import os

units_dictionary = {'microvolts': 1, 'raw': 2, 'gforce': 1}


class DisplayPlayback:
    start_time = 0
    stream_time = 0
    connection_attempt = 0
    gap_time = 0
    output_timing = True
    screen_dump = False

    @staticmethod
    def post_connection_issue(msg):
        sys.stdout.write("\r"+msg+" Retry attempt: #%d       " % DisplayPlayback.connection_attempt)
        sys.stdout.flush()
        DisplayPlayback.connection_attempt = DisplayPlayback.connection_attempt + 1

    @staticmethod
    def set_start_time(present_time):
        DisplayPlayback.start_time = present_time

    @staticmethod
    def playback_time_no_stream():
        if DisplayPlayback.output_timing:
            status = "Sending Data"
            if((time.time() - DisplayPlayback.stream_time) > 5):
                status = "Gap in Data"

            DisplayPlayback.write_to_terminal("\rPlayback Time: %.1fs : %s          " % ((time.time() - DisplayPlayback.start_time + DisplayPlayback.gap_time), status))

    @staticmethod
    def playback_error(msg):
        if DisplayPlayback.output_timing:
            status = "Sending Data"
            if((time.time() - DisplayPlayback.stream_time) > 5):
                status = "Gap in Data"
            DisplayPlayback.write_to_terminal("\rPlayback Time: %.1fs : %s           %s" % ((time.time() - DisplayPlayback.start_time + DisplayPlayback.gap_time), status, msg))

    @staticmethod
    def playback_time(current_playback_time, current_status):
        if DisplayPlayback.output_timing:
            DisplayPlayback.stream_time = time.time()
            DisplayPlayback.write_to_terminal("\rPlayback Time: %.1fs : %s          " % (current_playback_time, current_status))

    @staticmethod
    def end():
        DisplayPlayback.write_to_terminal(os.linesep)

    @staticmethod
    def print_msg(msg):
        try:
            sys.stdout.write(msg + os.linesep)
        except IOError:
            try:
                sys.stdout.close()
            except:
                pass
        except:
            pass

    @staticmethod
    def write_to_terminal(msg):
        if sys.stdout.isatty():
            DisplayPlayback.write_and_flush(msg)

    @staticmethod
    def write_and_flush(msg):
        if DisplayPlayback.screen_dump:
            #Removing \r (return) character in screen dump.
            msg = msg[1:]
        try:
            sys.stdout.write(msg)
            sys.stdout.flush()
        except IOError:
            try:
                sys.stdout.close()
            except:
                pass
        except:
            pass
