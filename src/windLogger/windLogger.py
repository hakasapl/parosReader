import os
import argparse
import json
import socket

from datetime import datetime,timedelta
from time import sleep

import ADS1263

#
# Deployment Parameters
#

MIN_WIND = 0  # Min wind speed of anemometer
MAX_WIND = 32.4  # Max wind speed of anemometer

MIN_V = 0.4  # Min voltage of anemometer output
MAX_V = 2.0  # Max voltage of anemometer output

REF = 5.08  # ADC reference voltage

ADC_INPUT = 0  # ADC input channel
FS = 20  # ADC sampling rate

#
# Main method
#
def main():
    parser = argparse.ArgumentParser(description='Logs anemometer data')
    parser.add_argument("-d", "--logDir",
                        type=str,
                        action="store",
                        default="./",
                        help="top level directory for log files, use \"\" around names with white space (default = ./)")

    #
    # parse user input
    #

    args = parser.parse_args()

    # initialize ADC
    ADC = ADS1263.ADS1263()

    if (ADC.ADS1263_init_ADC1('ADS1263_7200SPS') == -1):
        print("Unable to initialize ADC")
        exit(1)
    else:
        print("ADC Initialized")

    ADC.ADS1263_SetMode(0)

    #
    # get system info
    #
    cur_hostname = socket.gethostname()

    try:
        logFile = None

        logDirectoryName = os.path.join(args.logDir, "WINDLOG_{0:%Y%m%d}".format(datetime.utcnow()))
        if not os.path.exists(logDirectoryName):
            os.makedirs(logDirectoryName)
        
        print("\nWind logging started\nQuit with CTRL+C")

        # start at the next second
        lastTimestamp = datetime.utcnow()
        lastTimestamp += timedelta(seconds=1)
        lastTimestamp = lastTimestamp.replace(microsecond=0)
        while True:
            # wait for timestamp
            newTimestamp = lastTimestamp + timedelta(seconds=1/FS)
            if datetime.utcnow() < newTimestamp:
                continue

            if newTimestamp.date() != lastTimestamp.date():
                logDirectoryName = os.path.join(args.logDir, "WINDLOG_{0:%Y%m%d}".format(datetime.utcnow()))
                if not os.path.exists(logDirectoryName):
                    os.makedirs(logDirectoryName)

            lastTimestamp = newTimestamp

            ADC_value = ADC.ADS1263_GetChannalValue(ADC_INPUT)
            ADC_voltage = ADC_value * (REF / 0x7fffffff)

            wind_speed = (ADC_voltage - MIN_V) / (MAX_V - MIN_V)
            wind_speed *= MAX_WIND - MIN_WIND

            if wind_speed < 0:
                wind_speed = 0

            cur_timestamp = lastTimestamp.isoformat() + "Z"

            #
            # Send to log file
            #
            logFilePath = os.path.join(logDirectoryName, "WINDLOG_{0:%Y%m%d-%H}.txt".format(lastTimestamp))

            logFile = open(logFilePath, "a")

            logstring = cur_hostname + ",anemometer," + cur_timestamp + "," + str(ADC_value) + "," + str(ADC_voltage) + "," + str(wind_speed) + "\n"
            logFile.write(logstring)
    finally:
        print("Quitting...\n")
        logFile.close()
        ADC.ADS1263_Exit()

    # close rabbitmq connection
    if args.hostname != "":
        connection.close()

if __name__ == "__main__":
    main()
