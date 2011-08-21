#!/usr/bin/env python3

import os.path
import plistlib
import sqlite3
import time

from optparse import OptionParser
from subprocess import call
from tempfile import NamedTemporaryFile

# DBFILE = $HOME/.batterylogx.sqlite
DBFILE = os.path.join(os.environ['HOME'], '.batterylogx.sqlite')
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
        voltage = d['sppower_current_voltage']
        amperage = d['sppower_current_amperage']
        maxcap = chargeinfo['sppower_battery_max_capacity']
        is_charging = chargeinfo['sppower_battery_is_charging']
        capacity = chargeinfo['sppower_battery_current_capacity']
        bserial = batterymodel['sppower_battery_serial_number']
    return dict(voltage=voltage, amperage=amperage, maxcap=maxcap,
        is_charging=is_charging, capacity=capacity, bserial=bserial)

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

def main():
    parser = OptionParser()
    parser.add_option("-k", "--kill", dest="kill", action="store_true",
                      default=False, help="Kill a running logger")
    parser.add_option("-d", "--daemon", dest="daemon", action="store_true",
                      default=False, help="Run logger in background")

    (options, args) = parser.parse_args()
    if options.daemon:
        verbose = False
    else:
        verbose = True
        print("Logging to stdout and %s\n" % DBFILE)

    # Create the logging table if it doesn't exist
    create_table()

    # Main loop
    while True:
        log_data(verbose)
        time.sleep(30)

if __name__ == '__main__':
    main()