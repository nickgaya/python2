import argparse
import os
import sys

from python2.server.server import Python2Server


def parse_args(args=None):
    parser = argparse.ArgumentParser(description="Python 2 server")
    parser.add_argument('--in', '-i', dest='in_', type=int, default=0,
                        help="File descriptor for server input")
    parser.add_argument('--out', '-o', type=int, default=1,
                        help="File descriptor for server output")
    return parser.parse_args(args=args)


def run_server(conf):
    server = Python2Server(os.fdopen(conf.in_, 'rb'),
                           os.fdopen(conf.out, 'wb'))
    sys.stderr.write('Python 2 server started\n')
    server.run()
    sys.stderr.write('Python 2 server exited cleanly\n')


def main(args=None):
    conf = parse_args(args)
    run_server(conf)


if __name__ == '__main__':
    main()
