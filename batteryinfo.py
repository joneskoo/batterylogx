#!/usr/bin/env python3
# Copyright (C) 2011 by Joonas Kuorilehto
# License: MIT License

import os
import plistlib
import sys
import sqlite3
import time
from optparse import OptionParser
from subprocess import call
from tempfile import NamedTemporaryFile

# DBFILE = $HOME/.batterylogx.sqlite
DBFILE = os.path.join(os.environ['HOME'], '.batterylogx.sqlite')
PIDFILE = DBFILE.replace('sqlite', 'pid')
# Initialize database
conn = sqlite3.connect(DBFILE, isolation_level=None)
c = conn.cursor()

def getdata():
    with NamedTemporaryFile() as f:
        call(['system_profiler', '-xml', 'SPPowerDataType'], stdout=f)
        f.seek(0)
        p = plistlib.readPlist(f)
        d = p[0]['_items'][0]
        chargeinfo = d['sppower_battery_charge_info']
        batterymodel = d['sppower_battery_model_info']
        return dict(
            voltage=d['sppower_current_voltage'],
            amperage=d['sppower_current_amperage'],
            maxcap=chargeinfo['sppower_battery_max_capacity'],
            is_charging=chargeinfo['sppower_battery_is_charging'],
            capacity=chargeinfo['sppower_battery_current_capacity'],
            bserial=batterymodel['sppower_battery_serial_number'])

def create_table():
    '''Create the logging table if it does not exist'''
    try:
        c.execute('''CREATE TABLE batterylog (
            id SERIAL,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bserial TEXT,
            voltage INTEGER,
            amperage INTEGER,
            capacity INTEGER)''')
    except sqlite3.OperationalError:
        pass # table already created

def log_data(verbose=False):
    d = getdata()
    c.execute("""INSERT INTO batterylog
        (bserial, voltage, amperage, capacity) VALUES (?, ?, ?, ?)""",
        [d['bserial'], d['voltage'], d['amperage'], d['capacity']])
    if verbose:
        print("Voltage: %d mV  Amperage %d mA  Capacity %d mAh" % (
            d['voltage'], d['amperage'], d['capacity']))

def get_daemon_pid():
    '''Get daemon pid from pidfile and return it if it is running'''
    try:
        with open(PIDFILE, 'r') as f:
            try:
                pid = int(f.readline())
                os.kill(pid, 0)
            except ValueError:
                return None # Invalid pidfile content
            except OSError:
                return None # PID not running any more or not owned by us
        return pid
    except IOError:
        return None # File does not exist

def kill_daemon():
    '''Kill backgrounded daemon process and exit'''
    pid = get_daemon_pid()
    if pid:
        try:
            print("Killing backgrounded logger (pid %d)" % (pid))
            os.kill(pid, 15)
            return True
        except Exception as e:
            print("Failed:", str(e))
            return False
    else:
        print("Daemon not running or pidfile missing")
        return False

def mainloop(verbose):
    # Create the logging table if it doesn't exist
    create_table()

    # Main loop
    while True:
        log_data(verbose)
        time.sleep(30)

def daemonize(mainloop, *args):
    # http://code.activestate.com/recipes/66012/
    # do the UNIX double-fork magic, see Stevens' "Advanced
    # Programming in the UNIX Environment" for details (ISBN 0201563177)
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError as e:
        print >>sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)

    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent, print eventual PID before
            print("PID %d" % pid)
            with open(PIDFILE, 'w') as f:
                f.write("%d\n" % pid)
            sys.exit(0)
    except OSError as e:
        print >>sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)

    # start the daemon main loop
    mainloop(*args)

def main():
    parser = OptionParser()
    parser.add_option("-k", "--kill", dest="kill", action="store_true",
                      default=False, help="Kill a running logger")
    parser.add_option("-d", "--daemon", dest="daemon", action="store_true",
                      default=False, help="Run logger in background")

    (options, args) = parser.parse_args()

    if options.kill:
        if kill_daemon():
            sys.exit(0) # Killed successfully
        else:
            sys.exit(1) # Failed

    pid = get_daemon_pid()
    if pid:
        print("Already running (PID %d). Use -k to kill." % pid)
        sys.exit(1)

    if options.daemon:
        verbose = False
        print("OK, logging in background to %s." % DBFILE)
        daemonize(mainloop, verbose)
    else:
        verbose = True
        print("Logging to stdout and %s\n" % DBFILE)
        mainloop(verbose)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
