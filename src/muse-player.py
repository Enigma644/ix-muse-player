#!/usr/bin/python
import signal
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from input_handler import *
from output_handler import *
import Queue
import threading
import utilities
import platform
import sys

# XXX hack for pyinstaller
try:
    import h5py.h5ac
except:
    pass

input_handler = None
streaming_input_thread = None
output_handler = None
output_thread = None
args = None
done = False

VERSION = (1, 9, 1)

def prog_version_string():
    return "Muse Player v" + ".".join(str(x) for x in VERSION) + " [Unofficial Build by James Clutterbuck www.MuseMonitor.com]"

# Catch Control-C interrupt and cancel
def ix_signal_handler(signum, frame):
    utilities.DisplayPlayback.end()
    if input_handler:
        input_handler.put_done_message()
    if output_handler:
        output_handler.put_done_message()
    if output_thread:
        output_thread.join()
    print "Aborted."
    sys.exit()

def run_():
    global args, input_handler, streaming_input_thread, output_handler, output_thread
    parsing_streaming_input_thread = None
    streaming_input_thread = None
    output_thread = None
    done = False
    debug = False
    # Catch control-C
    signal.signal(signal.SIGINT, ix_signal_handler)
    if not 'Windows' in platform.platform():
        signal.signal(signal.SIGPIPE, ix_signal_handler)

    parser = ArgumentParser(description=prog_version_string(),
                            prog="muse-player.py",
                            usage="%(prog)s <one_input:(-l|-f|-o)> <one_or_more_outputs:[-s,-F,-M,-O,-D]>",
                            formatter_class=RawDescriptionHelpFormatter,
                            epilog="""

Examples:
    muse-player -f my_eeg_recording.muse -s osc.tcp://localhost:7887
        This will read in the file "my_eeg_recording.muse" and send those messages as OSC to port 7887.

    muse-player -l 5555 -M matlab.mat -s 5001
        This will receive OSC messages on port 5555, save them to file, and rebroadcast them to port 5001.
                            """)

    parser.add_argument("-v", "--verbose",
                        action="store_true",
                        dest="verbose",
                        default=False,
                        help="Print status messages to stdout")
    parser.add_argument("--version",
                        action="version",
                        version=prog_version_string())
    parser.add_argument("-q", "--as-fast-as-possible",
                        action="store_true",
                        dest="as_fast_as_possible",
                        default=False,
                        help="Replay input as fast as possible instead of using original timing.")

    parser.add_argument("-j", "--jump-data-gaps",
                        action="store_true",
                        dest="jump_data_gaps",
                        default=False,
                        help="Replay input by omitting any data gaps larger than 1 second.")

    parser.add_argument("-n", "--no--time--data",
                        action="store_true",
                        dest="no_time_data",
                        default=False,
                        help="Replay input by omitting output of current timing info.")

    parser.add_argument("-i", "--filter",
                        dest="filter_data",
                        nargs='+',
                        help="Filter data by path. e.g. -i /muse/elements/alpha /muse/eeg")

    input_group = parser.add_argument_group("Input options",
                                            "Only one type of input can be specified, but can be multiple files of the same type:")
    input_group.add_argument("-l", "--input-osc-port",
                             const="tcp:5000",
                             nargs='?',
                             help="Listen for OSC messages on this port (default: tcp:5000).")
    input_group.add_argument("-f", "--input-muse-files",
                             nargs='+',
                             help="Input from Muse file format.")
    input_group.add_argument("-o", "--input-oscreplay-files",
                             nargs='+',
                             help="Input from OSC-replay files.")

    output_group = parser.add_argument_group("Output options", "One or more outputs can be specified:")
    output_group.add_argument("-s", "--output-osc-url",
                              help="Output OSC messages to HOST:PORT (default: osc.udp://localhost:5001)",
                              const="osc.udp://localhost:5001",
                              nargs='?')
    output_group.add_argument("-F", "--output-muse-file",
                              help="Output to a Muse file",
                              metavar="FILE")
    output_group.add_argument("-M", "--output-matlab-file",
                              help="Output to a Matlab file",
                              metavar="FILE")
    output_group.add_argument("-O", "--output-oscreplay-file",
                              help="Output to an OSC-replay file",
                              metavar="FILE")
    output_group.add_argument("-C", "--output-csv-file",
                              help="Output to an CSV file",
                              metavar="FILE")
    output_group.add_argument("-D", "--output-screen-dump",
                              help="Output to the screen directly",
                              action='store_true')

    args = parser.parse_args()

    if args.no_time_data:
        utilities.DisplayPlayback.output_timing = False

    queue = Queue.Queue()
    input_handler = None
    output_handler = None

    print parser.description
    total_input_types = int(hasattr(args, 'input_osc_port')) + int(hasattr(args, 'input_muse_files')) + int(hasattr(args, 'input_osc_files'))
    total_input_types = int(bool(args.input_osc_port)) + int(bool(args.input_muse_files)) + int(bool(args.input_oscreplay_files))
    if total_input_types > 1:
        print >>sys.stderr, args.input_osc_port
        print >>sys.stderr, args.input_muse_files
        print >>sys.stderr, args.input_oscreplay_files
        parser.print_help(sys.stderr)
        print >>sys.stderr, '*' * 80
        print >>sys.stderr, ('ERROR: You can only specify one input type, you '
                             'specified ') + str(total_input_types)
        print >>sys.stderr, ""
        sys.exit(1)

    elif total_input_types == 0:
        parser.print_help(sys.stderr)
        print >>sys.stderr, '*' * 80
        print >>sys.stderr, ('ERROR: You have no input type, please specify '
                             'an input type.')
        print >>sys.stderr, ('Options are osc stream (-l port), muse file '
                             '(-f file) or osc replay file (-o file)')
        print >>sys.stderr, ''
        sys.exit(1)

    # Check for osc output stream enabled, if not default to writing the file
    # as fast as possible
    if args.output_osc_url == None:
        args.as_fast_as_possible = True
    
    print "Input: "
    if args.input_osc_port:
        print args.input_osc_port
        valid_options = ['udp', 'tcp']
        if len(args.input_osc_port.split(':')) == 1:
            if args.input_osc_port.lower() in valid_options:
                print "  * OSC port: {}:5000 (Hit Control-C to stop)".format(
                    args.input_osc_port)
            elif args.input_osc_port.isdigit():
                print "  * OSC port: tcp:{} (Hit Control-C to stop)".format(
                    args.input_osc_port)
            else:
                err = (
                    "Input error: You specified OSC listening at '{}' "
                    "tcp:port and udp:port are the only valid options"
                    ).format(args.input_osc_port)
                print >>sys.stderr, err
                sys.exit(1)
        else:
            port_options = args.input_osc_port.split(':')
            type = port_options[0]
            if not (type.lower() in valid_options):
                err = (
                    "Input port type error: You specified '{}' tcp "
                    "and udp are the only valid options"
                    ).format(port_options[0].lower())
                print >>sys.stderr, err
                sys.exit(1)
            elif port_options[1].isdigit():
                print "  * OSC port: {} (Hit Control-C to stop)".format(
                    args.input_osc_port)
            else:
                err = (
                    'Invalid port: {}, not a number, defaulting to port 5000'
                    ).format(port_options[1])
                print >>sys.stderr, err

                args.input_osc_port = port_options[0] + ':' + str(5000)
                print "  * OSC port: " + args.input_osc_port + " (Hit Control-C to stop)"
        input_handler = OSCListener(queue, args.input_osc_port)

    elif args.input_muse_files:
        input_handler = MuseProtoBufFileReader(queue)
        print "  * Muse file(s): " + str(args.input_muse_files)
    elif args.input_oscreplay_files:
        print args.input_oscreplay_files
        input_handler = MuseOSCFileReader(queue)
        parsing_streaming_input_thread = threading.Thread(target=input_handler.parse_files, args=[args.input_oscreplay_files])
        parsing_streaming_input_thread.daemon = True
        print "  * OSC file(s): " + str(args.input_oscreplay_files)

    print ""
    print "Output: "
    output_handler = OutputHandler(queue)
    if args.output_oscreplay_file:
        print "  * OSC-replay file: " + str(args.output_oscreplay_file)
        osc_writer = OSCFileWriter(args.output_oscreplay_file)
        output_handler.add_listener(osc_writer)
    if args.output_csv_file:
        print "  * CSV file: " + str(args.output_csv_file)
        csv_writer = CSVFileWriter(args.output_csv_file)
        output_handler.add_listener(csv_writer)
    if args.output_muse_file:
        print "  * Muse file: " + str(args.output_muse_file)
        proto_writer = ProtoBufFileWriter(args.output_muse_file)
        output_handler.add_listener(proto_writer)
    if args.output_osc_url:
        print "  * OSC output stream URL: " + str(args.output_osc_url)
        osc_sender = OSCMessageWriter(args.output_osc_url)
        output_handler.add_listener(osc_sender)
    if args.output_matlab_file:
        print "  * Matlab output file: " + str(args.output_matlab_file)
        matlab_writer = MatlabWriter(args.output_matlab_file)
        output_handler.add_listener(matlab_writer)

    total_output_types = int(bool(args.output_csv_file)) + int(bool(args.output_oscreplay_file)) + int(bool(args.output_muse_file)) + int(bool(args.output_osc_url)) + int(bool(args.output_matlab_file))
    if total_output_types == 0 or args.output_screen_dump:
        print "  * Screen output mode"
        utilities.DisplayPlayback.screen_dump = True
        screen_writer = ScreenWriter()
        output_handler.add_listener(screen_writer)

    if args.input_muse_files:
        parsing_streaming_input_thread = threading.Thread(target=input_handler.parse_files, args=[args.input_muse_files, args.verbose, args.as_fast_as_possible, args.jump_data_gaps])
        parsing_streaming_input_thread.daemon = True
        parsing_streaming_input_thread.start()

    if args.input_oscreplay_files:
        parsing_streaming_input_thread = threading.Thread(target=input_handler.parse_files, args=[args.input_oscreplay_files, args.verbose, args.as_fast_as_possible, args.jump_data_gaps])
        parsing_streaming_input_thread.daemon = True
        parsing_streaming_input_thread.start()

    if args.input_osc_port:
        streaming_input_thread = threading.Thread(target=input_handler.start, args=[args.as_fast_as_possible, args.jump_data_gaps])
        streaming_input_thread.daemon = True
    output_thread = threading.Thread(target=output_handler.start, args=[args.filter_data, args.verbose])
    output_thread.daemon = True


    if streaming_input_thread:
        streaming_input_thread.start()
    output_thread.start()

    while not done:
        try:
            status = "Gap in Data "
            if parsing_streaming_input_thread:
                parsing_streaming_input_thread.join(0.1)
                if not args.as_fast_as_possible:
                    utilities.DisplayPlayback.playback_time_no_stream()
            if streaming_input_thread:
                streaming_input_thread.join(0.1)
            output_thread.join(0.1)
            if streaming_input_thread:
                if not streaming_input_thread.isAlive() and not output_thread.isAlive():
                    done = True
            if parsing_streaming_input_thread:
                if not parsing_streaming_input_thread.isAlive() and not output_thread.isAlive():
                    done = True
        except BaseException as ex:
            #print ex.message
            done = True
            break

    data_parsed = 0
    data_in = 0
    data_out = 0
    if parsing_streaming_input_thread and args.input_muse_files:
        data_parsed = input_handler.events_added_by_threads
        data_in = input_handler.added_to_queue_events
        if args.output_matlab_file:
            data_out = matlab_writer.data_written
            if not data_in == data_out:
                print 'Input Output size mismatch:'
                print 'Data in: ' + str(data_in) + ' Data out: ' + str(data_out) + " File: " + str(args.input_muse_files)

# If invoked as a script
if __name__ == "__main__":
    run_()
