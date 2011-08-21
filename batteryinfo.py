#!/usr/bin/env python3

import os.path
import plistlib
import sqlite3
import time

from subprocess import call
from tempfile import NamedTemporaryFile

# DBFILE = $HOME/.batterylogx.sqlite
DBFILE = os.path.join(os.environ['HOME'], '.batterylogx.sqlite')

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
    return {'voltage' : voltage, 'amperage': amperage, 'maxcap' : maxcap,
        'is_charging' : is_charging, 'capacity' : capacity,
        'bserial' : bserial}

def main():
    # Initialize database
    conn = sqlite3.connect(DBFILE, isolation_level=None)
    c = conn.cursor()
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

    # Main loop
    while True:
        d = getdata()
        c.execute("""INSERT INTO batterylog
            (bserial, voltage, amperage, capacity) VALUES (?, ?, ?, ?)""",
            [d['bserial'], d['voltage'], d['amperage'], d['capacity']])
        time.sleep(30)

if __name__ == '__main__':
    main()