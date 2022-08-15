#!/usr/bin/env python
import time
import sys
import os
import datetime
from datetime import datetime
import glob
import argparse
import pika
import json
import socket

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

parser = argparse.ArgumentParser(description='Logs anemometer data')
parser.add_argument("-d", "--logDir",
                    type=str,
                    action="store",
                    default="./",
                    help="top level directory for log files, use \"\" around names with white space (default = ./)")
parser.add_argument("-i", "--hostname", help="Address of remote rabbitmq server", type=str, default="")
parser.add_argument("-u", "--username", help="Username of remote rabbitmq server", type=str, default="")
parser.add_argument("-p", "--password", help="Password of remote rabbitmq server", type=str, default="")
parser.add_argument("-q", "--queue", help="Rabbitmq queue to submit to", type=str, default="parosLogger")

#
# parse user input
#

args = parser.parse_args()

#
# get system info
#
cur_hostname = socket.gethostname()

if args.hostname != "":
    credentials = pika.PlainCredentials(args.username, args.password)
    connection = pika.BlockingConnection(pika.ConnectionParameters(args.hostname, credentials=credentials))
    channel = connection.channel()

    channel.queue_declare(queue=args.queue)

#while True:
# initialize current hour to a negative number to force a new log file with first sample
try:
    verbose = False
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
            logDirectoryName = os.path.join(args.logDir, "WXLOG-{0:%Y%m%d}".format(datetime.utcnow()))
            print('logDir name {0}'.format(logDirectoryName))
            if not os.path.exists(logDirectoryName):
                os.makedirs(logDirectoryName)
            logFileName = "WX-{0:%Y%m%d-%H%M%S}.txt".format(datetime.utcnow())
            print('logFile name {0}'.format(logFileName))
            logFilePath = os.path.join(logDirectoryName, logFileName)
            print('logFile path {0}'.format(logFilePath))
            print("  opening log file: " + logFilePath + "\n")
            logFile = open(logFilePath, "w")
        # Read the last ADC conversion value and print it out.
        value = adc.get_last_result()
        voltage = value*0.0001250038148/GAIN
        voltage = round(voltage, 10)
        speed = voltage*20.25-8.1-.06
        speed = round(speed, 10)
        cur_timestamp = '{0:%m/%d/%y %H:%M:%S.000}'.format(datetime.utcnow())

        if verbose:
            print('{0:.5f}vdc {1:.1f}m/s'.format(voltage, speed))
        
        # send to rabbitmq, if set
        if args.hostname != "":
            mq_msg_json = {
                "module_id": cur_hostname,
                "sensor_id": "anemometer",
                "timestamp": cur_timestamp,
                "voltage": voltage,
                "value": speed
            }
            
            channel.basic_publish(exchange='', routing_key=args.queue, body=json.dumps(mq_msg_json))

        datastring = cur_timestamp + "," + str(voltage) + "," + str(speed)
        print(datastring)
        logFile.write(datastring)
        #logFile.write("test")
        # Sleep for half a second.
        time.sleep(1.0)
finally:
    print("Quitting...\n")
    logFile.close()
    adc.stop_adc()

# close rabbitmq connection
if args.hostname != "":
    connection.close()