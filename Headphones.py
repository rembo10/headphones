#!/usr/bin/env python
#  This file is part of Headphones.
#
#  Headphones is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Headphones is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Headphones.  If not, see <http://www.gnu.org/licenses/>.

import os, sys, locale
import time
import signal

from lib.configobj import ConfigObj

import headphones

from headphones import webstart, logger

try:
    import argparse
except ImportError:
    import lib.argparse as argparse

signal.signal(signal.SIGINT, headphones.sig_handler)
signal.signal(signal.SIGTERM, headphones.sig_handler)


def main():

    # Fixed paths to Headphones
    if hasattr(sys, 'frozen'):
        headphones.FULL_PATH = os.path.abspath(sys.executable)
    else:
        headphones.FULL_PATH = os.path.abspath(__file__)

    headphones.PROG_DIR = os.path.dirname(headphones.FULL_PATH)
    headphones.ARGS = sys.argv[1:]

    # From sickbeard
    headphones.SYS_PLATFORM = sys.platform
    headphones.SYS_ENCODING = None

    try:
        locale.setlocale(locale.LC_ALL, "")
        headphones.SYS_ENCODING = locale.getpreferredencoding()
    except (locale.Error, IOError):
        pass

    # for OSes that are poorly configured I'll just force UTF-8
    if not headphones.SYS_ENCODING or headphones.SYS_ENCODING in ('ANSI_X3.4-1968', 'US-ASCII', 'ASCII'):
        headphones.SYS_ENCODING = 'UTF-8'

    # Set up and gather command line arguments
    parser = argparse.ArgumentParser(description='Music add-on for SABnzbd+')

    parser.add_argument('-v', '--verbose', action='store_true', help='Increase console logging verbosity')
    parser.add_argument('-q', '--quiet', action='store_true', help='Turn off console logging')
    parser.add_argument('-d', '--daemon', action='store_true', help='Run as a daemon')
    parser.add_argument('-p', '--port', type=int, help='Force Headphones to run on a specified port')
    parser.add_argument('--datadir', help='Specify a directory where to store your data files')
    parser.add_argument('--config', help='Specify a config file to use')
    parser.add_argument('--nolaunch', action='store_true', help='Prevent browser from launching on startup')
    parser.add_argument('--pidfile', help='Create a pid file (only relevant when running as a daemon)')

    args = parser.parse_args()

    if args.verbose:
        headphones.VERBOSE = 2
    elif args.quiet:
        headphones.VERBOSE = 0

    if args.daemon:
        if sys.platform == 'win32':
            print "Daemonize not supported under Windows, starting normally"
        else:
            headphones.DAEMON=True
            headphones.VERBOSE = False

    if args.pidfile:
        headphones.PIDFILE = str(args.pidfile)

        # If the pidfile already exists, headphones may still be running, so exit
        if os.path.exists(headphones.PIDFILE):
            sys.exit("PID file '" + headphones.PIDFILE + "' already exists. Exiting.")

        # The pidfile is only useful in daemon mode, make sure we can write the file properly
        if headphones.DAEMON:
            headphones.CREATEPID = True
            try:
                file(headphones.PIDFILE, 'w').write("pid\n")
            except IOError, e:
                raise SystemExit("Unable to write PID file: %s [%d]" % (e.strerror, e.errno))
        else:
            logger.warn("Not running in daemon mode. PID file creation disabled.")

    if args.datadir:
        headphones.DATA_DIR = args.datadir
    else:
        headphones.DATA_DIR = headphones.PROG_DIR

    if args.config:
        headphones.CONFIG_FILE = args.config
    else:
        headphones.CONFIG_FILE = os.path.join(headphones.DATA_DIR, 'config.ini')

    # Try to create the DATA_DIR if it doesn't exist
    if not os.path.exists(headphones.DATA_DIR):
        try:
            os.makedirs(headphones.DATA_DIR)
        except OSError:
            raise SystemExit('Could not create data directory: ' + headphones.DATA_DIR + '. Exiting....')

    # Make sure the DATA_DIR is writeable
    if not os.access(headphones.DATA_DIR, os.W_OK):
        raise SystemExit('Cannot write to the data directory: ' + headphones.DATA_DIR + '. Exiting...')

    # Put the database in the DATA_DIR
    headphones.DB_FILE = os.path.join(headphones.DATA_DIR, 'headphones.db')

    headphones.CFG = ConfigObj(headphones.CONFIG_FILE, encoding='utf-8')

    # Read config & start logging
    headphones.initialize()

    if headphones.DAEMON:
        if sys.platform == "win32":
            print "Daemonize not supported under Windows, starting normally"
        else:
            headphones.daemonize()

    #configure the connection to the musicbrainz database
    headphones.mb.startmb()

    # Force the http port if neccessary
    if args.port:
        http_port = args.port
        logger.info('Starting Headphones on forced port: %i' % http_port)
    else:
        http_port = int(headphones.HTTP_PORT)

    # Try to start the server.
    webstart.initialize({
                    'http_port':        http_port,
                    'http_host':        headphones.HTTP_HOST,
                    'http_root':        headphones.HTTP_ROOT,
                    'http_proxy':       headphones.HTTP_PROXY,
                    'http_username':    headphones.HTTP_USERNAME,
                    'http_password':    headphones.HTTP_PASSWORD,
            })

    logger.info('Starting Headphones on port: %i' % http_port)

    if headphones.LAUNCH_BROWSER and not args.nolaunch:
        headphones.launch_browser(headphones.HTTP_HOST, http_port, headphones.HTTP_ROOT)

    # Start the background threads
    headphones.start()

    while True:
        if not headphones.SIGNAL:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                headphones.SIGNAL = 'shutdown'
        else:
            logger.info('Received signal: ' + headphones.SIGNAL)
            if headphones.SIGNAL == 'shutdown':
                headphones.shutdown()
            elif headphones.SIGNAL == 'restart':
                headphones.shutdown(restart=True)
            else:
                headphones.shutdown(restart=True, update=True)

            headphones.SIGNAL = None

    return

if __name__ == "__main__":
    main()
