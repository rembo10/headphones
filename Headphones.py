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

import os
import sys

# Ensure lib added to path, before any other imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib/'))

from headphones import webstart, logger

import locale
import time
import signal
import argparse
import headphones

# Register signals, such as CTRL + C
signal.signal(signal.SIGINT, headphones.sig_handler)
signal.signal(signal.SIGTERM, headphones.sig_handler)


def main():
    """
    Headphones application entry point. Parses arguments, setups encoding and
    initializes the application.
    """

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
    parser = argparse.ArgumentParser(
        description='Music add-on for SABnzbd+, Transmission and more.')

    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Increase console logging verbosity')
    parser.add_argument(
        '-q', '--quiet', action='store_true', help='Turn off console logging')
    parser.add_argument(
        '-d', '--daemon', action='store_true', help='Run as a daemon')
    parser.add_argument(
        '-p', '--port', type=int, help='Force Headphones to run on a specified port')
    parser.add_argument(
        '--datadir', help='Specify a directory where to store your data files')
    parser.add_argument('--config', help='Specify a config file to use')
    parser.add_argument('--nolaunch', action='store_true',
                        help='Prevent browser from launching on startup')
    parser.add_argument(
        '--pidfile', help='Create a pid file (only relevant when running as a daemon)')

    args = parser.parse_args()

    if args.verbose:
        headphones.VERBOSE = True
    if args.quiet:
        headphones.QUIET = True

    # Do an intial setup of the logger.
    logger.initLogger(console=not headphones.QUIET, log_dir=False,
        verbose=headphones.VERBOSE)

    if args.daemon:
        if sys.platform == 'win32':
            sys.stderr.write(
                "Daemonizing not supported under Windows, starting normally\n")
        else:
            headphones.DAEMON = True
            headphones.QUIET = True

    if args.pidfile:
        headphones.PIDFILE = str(args.pidfile)

        # If the pidfile already exists, headphones may still be running, so
        # exit
        if os.path.exists(headphones.PIDFILE):
            raise SystemExit("PID file '%s' already exists. Exiting." %
                headphones.PIDFILE)

        # The pidfile is only useful in daemon mode, make sure we can write the
        # file properly
        if headphones.DAEMON:
            headphones.CREATEPID = True

            try:
                with open(headphones.PIDFILE, 'w') as fp:
                    fp.write("pid\n")
            except IOError as e:
                raise SystemExit("Unable to write PID file: %s", e)
        else:
            logger.warn("Not running in daemon mode. PID file creation " \
                "disabled.")

    # Determine which data directory and config file to use
    if args.datadir:
        headphones.DATA_DIR = args.datadir
    else:
        headphones.DATA_DIR = headphones.PROG_DIR

    if args.config:
        config_file = args.config
    else:
        config_file = os.path.join(headphones.DATA_DIR, 'config.ini')

    # Try to create the DATA_DIR if it doesn't exist
    if not os.path.exists(headphones.DATA_DIR):
        try:
            os.makedirs(headphones.DATA_DIR)
        except OSError:
            raise SystemExit(
                'Could not create data directory: ' + headphones.DATA_DIR + '. Exiting....')

    # Make sure the DATA_DIR is writeable
    if not os.access(headphones.DATA_DIR, os.W_OK):
        raise SystemExit(
            'Cannot write to the data directory: ' + headphones.DATA_DIR + '. Exiting...')

    # Put the database in the DATA_DIR
    headphones.DB_FILE = os.path.join(headphones.DATA_DIR, 'headphones.db')

    # Read config and start logging
    headphones.initialize(config_file)

    if headphones.DAEMON:
        headphones.daemonize()

    # Configure the connection to the musicbrainz database
    headphones.mb.startmb()

    # Force the http port if neccessary
    if args.port:
        http_port = args.port
        logger.info('Using forced web server port: %i', http_port)
    else:
        http_port = int(headphones.CONFIG.HTTP_PORT)

    # Check if pyOpenSSL is installed. It is required for certificate generation
    # and for CherryPy.
    if headphones.CONFIG.ENABLE_HTTPS:
        try:
            import OpenSSL
        except ImportError:
            logger.warn("The pyOpenSSL module is missing. Install this " \
                "module to enable HTTPS. HTTPS will be disabled.")
            headphones.CONFIG.ENABLE_HTTPS = False

    #This fix is put in place for systems with broken SSL (like QNAP)
    certificate_verification = headphones.CONFIG.VERIFY_SSL_CERT
    if not certificate_verification:
        try:
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
        except:
            pass
    #==== end block (should be configurable at settings level)

    # Try to start the server. Will exit here is address is already in use.
    web_config = {
        'http_port': http_port,
        'http_host': headphones.CONFIG.HTTP_HOST,
        'http_root': headphones.CONFIG.HTTP_ROOT,
        'http_proxy': headphones.CONFIG.HTTP_PROXY,
        'enable_https': headphones.CONFIG.ENABLE_HTTPS,
        'https_cert': headphones.CONFIG.HTTPS_CERT,
        'https_key': headphones.CONFIG.HTTPS_KEY,
        'http_username': headphones.CONFIG.HTTP_USERNAME,
        'http_password': headphones.CONFIG.HTTP_PASSWORD,
    }
    webstart.initialize(web_config)

    # Start the background threads
    headphones.start()

    # Open webbrowser
    if headphones.CONFIG.LAUNCH_BROWSER and not args.nolaunch:
        headphones.launch_browser(headphones.CONFIG.HTTP_HOST, http_port,
                                  headphones.CONFIG.HTTP_ROOT)

    # Wait endlessy for a signal to happen
    while True:
        if not headphones.SIGNAL:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                headphones.SIGNAL = 'shutdown'
        else:
            logger.info('Received signal: %s', headphones.SIGNAL)

            if headphones.SIGNAL == 'shutdown':
                headphones.shutdown()
            elif headphones.SIGNAL == 'restart':
                headphones.shutdown(restart=True)
            else:
                headphones.shutdown(restart=True, update=True)

            headphones.SIGNAL = None

# Call main()
if __name__ == "__main__":
    main()
