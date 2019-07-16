#!/usr/bin/env python3
import time
import sys
import os
import datetime
from datetime import datetime
import glob
import argparse

# Import the ADS1x15 module.
import Adafruit_ADS1x15

# Create an ADS1115 ADC (16-bit) instance.
adc = Adafruit_ADS1x15.ADS1115(address=0x48, busnum=1)

#  - 2/3 = +/-6.144V
#  -   1 = +/-4.096V
#  -   2 = +/-2.048V
#  -   4 = +/-1.024V
#  -   8 = +/-0.512V
#  -  16 = +/-0.256V
GAIN = 2

# Start continuous ADC conversions on channel 0 using the previously set gain
# value.  Note you can also pass an optional data_rate parameter, see the simpletest.py
# example and read_adc function for more infromation.
adc.start_adc(0, gain=GAIN)


#while True:
# initialize current hour to a negative number to force a new log file with first sample
try:
    logFile = None
    currentUTCHour = -1
    print("\nRunning...quit with ctrl-C...\n")
    while True:
        #
        # open a new log file on change in hour of day
        #
        #                if datetime.utcnow().minute != currentUTCHour:
        #                    currentUTCHour = datetime.utcnow().minute
        if datetime.utcnow().hour != currentUTCHour:
            currentUTCHour = datetime.utcnow().hour
            if logFile is not None:
                print('log file is not None')
                logFile.close()
            logDirectoryName = "WindSpeedLog-{0:%Y%m%d}".format(datetime.utcnow())
            print('logDir name {0}'.format(logDirectoryName))
            if not os.path.exists(logDirectoryName):
                os.makedirs(logDirectoryName)
            logFileName = "WS-{0:%Y%m%d-%H%M%S}.txt".format(datetime.utcnow())
            print('logFile name {0}'.format(logFileName))
            logFilePath = os.path.join(logDirectoryName, logFileName)
            print('logFile path {0}'.format(logFilePath))
            print("  opening log file: " + logFilePath + "\n")
            logFile = open(logFilePath, "w")
            print(type(logFile))
        # Read the last ADC conversion value and print it out.
        value = adc.get_last_result()
        voltage = value*0.0001250038148/GAIN
        speed = voltage*20.25-8.1-.06
        datastring = '{0:%Y%m%d-%H%M%S}: Channel 0: {1:.5f} volts, {2:.1f} m/s\n'.format(datetime.utcnow() , voltage, speed)
        print('Channel 0: {0:.5f} volts, {1:.1f} m/s'.format(voltage, speed))
        logFile.write(datastring)
        #logFile.write("test")
        # Sleep for half a second.
        time.sleep(0.5)
finally:
    print("Quitting...\n")
    logFile.close()
    adc.stop_adc()
