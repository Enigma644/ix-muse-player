import h5_eq
from argparse import ArgumentParser, RawDescriptionHelpFormatter

if __name__ == "__main__":
    print """
    This script will print out any differences between two MATLAB files.
    For paths that match, it will simply show the path.
    """
    parser = ArgumentParser(description="",
                        prog="matlab_checker.py",
                        usage="%(prog)s <MATLAB_file_1> <MATLAB_file_2>",
                        formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("file1")
    parser.add_argument("file2")
    args = parser.parse_args()
    result = h5_eq.files_match(args.file1, args.file2)
    if result:
        print "\nFiles match!\n"
    else:
        print "\nDifferences found in the two files.\n"