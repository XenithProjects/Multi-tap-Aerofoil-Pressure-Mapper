"""
serial_logger.py

Logs CSV pressure data streamed from the ESP32 (aerofoil_scanner_serial.ino)
to a local CSV file, for later Cp post-processing.

Requires: pip install pyserial

Usage:
    python serial_logger.py --port COM5
    python serial_logger.py --port /dev/ttyUSB0 --duration 30
"""

import argparse
import csv
import sys
import time
from datetime import datetime

import serial


def main():
    parser = argparse.ArgumentParser(description="Log SDP810 mux data over serial to CSV.")
    parser.add_argument("--port", required=True, help="Serial port, e.g. COM5 or /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default 115200)")
    parser.add_argument("--outfile", default=None, help="Output CSV filename")
    parser.add_argument("--duration", type=float, default=None,
                         help="Seconds to log before auto-stopping (default: run until Ctrl+C)")
    args = parser.parse_args()

    outfile = args.outfile or f"aerofoil_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    print(f"Connecting to {args.port} at {args.baud} baud...")
    ser = serial.Serial(args.port, args.baud, timeout=1)
    time.sleep(2)  # allow ESP32 to reset after serial connection opens

    header_written = False
    start_time = time.time()
    row_count = 0

    with open(outfile, "w", newline="") as f:
        writer = csv.writer(f)
        print(f"Logging to {outfile} ... Ctrl+C to stop\n")

        try:
            while True:
                if args.duration is not None and (time.time() - start_time) > args.duration:
                    print(f"\nReached duration limit of {args.duration}s, stopping.")
                    break

                raw = ser.readline().decode(errors="ignore").strip()
                if not raw:
                    continue

                # Only process our tagged data/header rows; ignore diagnostic '#' lines
                if raw.startswith("DATA,"):
                    fields = raw[len("DATA,"):].split(",")

                    if fields[0] == "time_ms" and not header_written:
                        writer.writerow(fields)
                        header_written = True
                        print("Header:", ",".join(fields))
                        continue

                    if fields[0] == "time_ms":
                        continue  # duplicate header line, skip

                    writer.writerow(fields)
                    row_count += 1
                    if row_count % 10 == 0:
                        print(f"[{row_count} rows] {raw}")
                else:
                    # Startup/diagnostic messages from the ESP32
                    print(raw)

        except KeyboardInterrupt:
            print("\nStopped by user.")

    print(f"\nDone. {row_count} data rows written to {outfile}")


if __name__ == "__main__":
    try:
        main()
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        print("Check that the port name is correct and no other program (e.g. Arduino Serial Monitor) has it open.")
        sys.exit(1)
