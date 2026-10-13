#!/usr/bin/env python3
"""Continuous data acquisition test for ONE TMP100 sensor.

Standalone hardware check - no threading, no project imports.

    python3 tmp100_read.py                # 0x4f, one reading per second
    python3 tmp100_read.py 0.5            # one reading every 0.5 s
    python3 tmp100_read.py 0.5 60         # every 0.5 s, stop after 60 s
    python3 tmp100_read.py 1 0 0x48       # every 1 s, no time limit, address 0x48

A duration of 0 means "keep going until Ctrl-C".
Ctrl-C stops it early; a summary prints either way.
"""
import sys
import time

from smbus2 import SMBus

CHANNEL = 1              # I2C bus (Raspberry Pi: 1)
ADDRESS = 0x4F           # TMP100 address, set by the ADD0/ADD1 pins
TEMP_REG = 0x00
CONFIG_REG = 0x01
CONFIG_12BIT = 0b1100000  # 12-bit resolution -> 0.0625 degC per count


def read_temp_c(bus, addr):
    """One temperature in degrees C. Raises OSError if the sensor does not answer."""
    data = bus.read_i2c_block_data(addr, TEMP_REG, 2)
    temp = ((data[0] << 8) + (data[1] & 0b11110000)) >> 4   # 12-bit, left-justified
    if temp > 2047:                                          # two's complement
        temp -= 4096
    return temp * 0.0625


def main():
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else None
    address = int(sys.argv[3], 0) if len(sys.argv) > 3 else ADDRESS
    if duration is not None and duration <= 0:
        duration = None   # 0 means "no time limit", so an address can be passed alone

    with SMBus(CHANNEL) as bus:
        try:
            bus.write_byte_data(address, CONFIG_REG, CONFIG_12BIT)
        except OSError as exc:
            raise SystemExit(
                "No TMP100 answered at %s on bus %d (%s).\n"
                "Check wiring and pull-ups, then run:  i2cdetect -y %d"
                % (hex(address), CHANNEL, exc, CHANNEL))
        time.sleep(0.32)   # first 12-bit conversion takes about 320 ms

        print("Reading %s on I2C bus %d every %g s. Ctrl-C to stop.\n"
              % (hex(address), CHANNEL, interval))
        print("%-10s %10s" % ("elapsed", "temp (C)"))
        print("-" * 21)

        readings, errors = [], 0
        start = time.monotonic()
        try:
            while duration is None or time.monotonic() - start < duration:
                elapsed = time.monotonic() - start
                try:
                    temp = read_temp_c(bus, address)
                    readings.append(temp)
                    print("%9.1fs %10.3f" % (elapsed, temp), flush=True)
                except OSError as exc:
                    errors += 1
                    print("%9.1fs %10s   <- %s" % (elapsed, "ERR", exc), flush=True)
                time.sleep(interval)
        except KeyboardInterrupt:
            pass

        total = time.monotonic() - start
        print("\n%d reading(s) over %.1f s, %d failed" % (len(readings), total, errors))
        if readings:
            print("min %.3f C   max %.3f C   mean %.3f C"
                  % (min(readings), max(readings), sum(readings) / len(readings)))


if __name__ == "__main__":
    main()
