#! /bin/sh

### BEGIN INIT INFO
# Provides:          Headphones application instance
# Required-Start:    $all
# Required-Stop:     $all
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: starts instance of Headphones
# Description:       starts instance of Headphones using start-stop-daemon
### END INIT INFO

############### EDIT ME ##################
# path to app
APP_PATH=/usr/local/sbin/headphones

# path to python bin
DAEMON=/usr/bin/python

# startup args
DAEMON_OPTS=" Headphones.py -q"

# script name
NAME=headphones

# app name
DESC=headphones

# user
RUN_AS=root

PID_FILE=/var/run/headphones.pid

############### END EDIT ME ##################

test -x $DAEMON || exit 0

set -e

case "$1" in
  start)
        echo "Starting $DESC"
        start-stop-daemon -d $APP_PATH -c $RUN_AS --start --background --pidfile $PID_FILE  --make-pidfile --exec $DAEMON -- $DAEMON_OPTS
        ;;
  stop)
        echo "Stopping $DESC"
        start-stop-daemon --stop --pidfile $PID_FILE
        ;;

  restart|force-reload)
        echo "Restarting $DESC"
        start-stop-daemon --stop --pidfile $PID_FILE
        sleep 15
        start-stop-daemon -d $APP_PATH -c $RUN_AS --start --background --pidfile $PID_FILE  --make-pidfile --exec $DAEMON -- $DAEMON_OPTS
        ;;
  *)
        N=/etc/init.d/$NAME
        echo "Usage: $N {start|stop|restart|force-reload}" >&2
        exit 1
        ;;
esac

exit 0
