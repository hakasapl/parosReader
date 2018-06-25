#!/usr/bin/env python3
#
# dqLoggerP4.py - Python script to log Paroscientific DigiQuartz barometer data
#               - Assumes model 6000-16B-IS barometers
#               - Uses P4 continuous sampling
#
#   usage: ./dqLoggerP4.py [-h] [-t] [-v] [-d LOGDIR]
#
#   D.L. Pepyne and Westy
#   Copyright 2018 __University of Massachusetts__. All rights reserved.
#
#   Revision: 19 March 2018; 1 May 2018; 8 May 2018; 9 May 2018; 12 May 2018; 4 June 2018;
#             7 June 2018; 8 June 2018; 23 June 2018; 24 June 2018; 25 June 2018
#

import time
import serial
import serial.tools.list_ports
import sys
import glob
import os
import argparse
import datetime
from datetime import datetime
import numpy as np

#
# class to read a line of data - this class is claimed to be more efficient than
# the pyserial readline - obtains higher throughput and works better with Raspberry
# Pis and Arduinos - as is, it does not have a timeout and will hang if a barometer
# loses power or otherwise fails to respond - here we've modified the original code
# to return on serial port timeout
#
# orignal code obtained from: https://github.com/pyserial/pyserial/issues/216
#

class ReadLine:
    def __init__(self, s):
        self.buf = bytearray()
        self.s = s
    
    def readline(self):
        i = self.buf.find(b"\n")
        if i >= 0:
            r = self.buf[:i+1]
            self.buf = self.buf[i+1:]
            return r
        while True:
            i = max(1, min(2048, self.s.in_waiting))
            data = self.s.read(i)
            
            # return on serial port timeout
            if not data:
                return data

            i = data.find(b"\n")
            if i >= 0:
                r = self.buf + data[:i+1]
                self.buf[0:] = data[i+1:]
                return r
            else:
                self.buf.extend(data)

#
# function to send a barometer command and return the response - waitFlag = 1 returns
# only if there's data (use when configuring a barometer) - waitFlag = 0 returns with
# an empty string on serial port timeout (use when looking for barometers)
#

def sendCommand(strOut, dqPort, waitFlag, verbosemodeFlag):
    if verbosemodeFlag:
        print("    command: " + strOut)
    strOut = strOut + '\r\n'
    binOut = strOut.encode()
    dqPort.write(binOut)
    while True:
        binIn = dqPort.readline()
        strIn = binIn.decode()
        if not strIn:
            if not waitFlag:
                break
            elif verbosemodeFlag:
                print("    WAITING FOR CONFIGURATION RESPONSE")
        else:
            break
    if verbosemodeFlag:
        print("    response: " + strIn[:-2])
    return strIn[5:-2]

#
# main method
#

def main():

    #
    # define parser for user input
    #

    parser = argparse.ArgumentParser(description='Logs regularly sampled barometer pressure data. Assumes Model 6000-16B-IS Paroscientific DigiQuartz barometers.')
    parser.add_argument("-t", "--test",
                        help="print barometer data to console rather than saving to log file",
                        action="store_true")
    parser.add_argument("-v", "--verbose",
                        help="show verbose output",
                        action="store_true")
    parser.add_argument("-d", "--logDir",
                        type=str,
                        action="store",
                        default="./",
                        help="top level directory for log files, use \"\" around names with white space (default = ./)")

    #
    # parse user input
    #

    args = parser.parse_args()

    print("\nParsing user inputs...\n")

    if args.test:
        testmodeFlag = 1
        print("  test mode          = TRUE")
    else:
        testmodeFlag = 0
        print("  test mode          = FALSE")

    if args.verbose:
        verbosemodeFlag = 1
        print("  verbose mode       = TRUE")
    else:
        verbosemodeFlag = 0
        print("  verbose mode       = FALSE")

    logDir = args.logDir

    if not os.path.isdir(logDir):
        print("  log file directory \"" + logDir + "\" does not exist\n")
        print("Quitting\n")
        exit()

    print("  log file directory = " + logDir)

    #
    # get list of usbserial ports, quit if none found
    #
    
    print("\nChecking for usbserial ports...\n")

    usbPortList = []
    # for Raspberry PI
    if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        portList = glob.glob('/dev/tty[A-Za-z]*')
        for port in portList:
            if "USB" in port:
                usbPortList.append(port)
    # for OSX
    elif sys.platform.startswith('darwin'):
        portList = serial.tools.list_ports.comports()
        for port in portList:
            if "usbserial" in port.device:
                usbPortList.append(port.device)
    else:
        raise EnvironmentError('Unsupported platform')

    if usbPortList:
        for usbPort in usbPortList:
            print("  found: " + usbPort)
    else:
        print("  no usbserial ports found\n")
        print("Quitting\n")
        exit()

    #
    # check usbserial ports for barometers, quit if none
    #
    
    print("\nChecking for barometers...\n")

    dqPortList = []
    dqSerialNumberList = []
    for usbPort in usbPortList:
        print("  checking: " + usbPort)
        dqPort = serial.Serial()
        dqPort.port = usbPort
        if dqPort.isOpen():
            dqPort.close()
        dqPort.baudrate = 115200
        dqPort.bytesize = serial.EIGHTBITS
        dqPort.parity = serial.PARITY_NONE
        dqPort.stopbits = serial.STOPBITS_ONE
        dqPort.timeout = 0.2  # needs to be long enough to wake barometer and get response
        dqPort.open()

        waitFlag = 0  # no response within timeout --> no barometer

        dqModelNumber = sendCommand('*0100MN', dqPort, waitFlag, verbosemodeFlag)
        if "6000-16B-IS" in dqModelNumber:
            tempStr = sendCommand('*0100SN', dqPort, waitFlag, verbosemodeFlag)
            dqSerialNumber = tempStr[3:]
            print("    found serial number:\tSN=" + dqSerialNumber)
            dqPortList.append(dqPort)
            dqSerialNumberList.append(dqSerialNumber)
        else:
            dqPort.close()

    if dqPortList:
        numBarometers = len(dqPortList)
        print("\n  " + str(numBarometers) + " barometer(s) found")
    else:
        print("\n  no 6000-16B-IS barometer(s) found\n")
        print("Quitting\n")
        exit()

    #
    # configure barometers for infrasound sampling
    #
    # NOTE - because barometer EPROM can only be written a finite
    # number of times, configuration settings should ONLY be changed
    # if they are not already set as desired - since the
    # barometers came from the factory correctly configured for
    # infrasound sampling, the code currently only allows changes
    # to the sample rate and anti-alias cutoff filter frequency
    # - in particular, for the wind profiler experiments we keep the
    # factory sample rate of 20 Hz, but increase the anti-alias filter
    # cutoff from the factory IA=7 (4 Hz cutoff) to IA=6 (8 Hz cutoff)
    #
    # NOTE - in tests on MacBook Pro max sample rate seems to be about
    # 40 Hz - above that get lots of barometer TIMEOUTS
    #
    # desired configuration settings:
    #
    # - nano-resolution mode:          XM=1, enabled
    # - pressure units:                UN=2, hPa
    # - data output mode:              MD=0, model 715 display data output off
    # - number of significant digits:  XN=0, use default number of significant digits
    # - timestamp flag:                TS=1, timestamps enabled
    # - GPS interface flag:            GE=1, GPS interface enabled
    # - timestamp format:              TJ=0, default millisecond timestamp format
    # - timezone offset:               TF=0, use UTC time
    # - timestamp position:            TP=0, timestamp before pressure
    # - time format:                   GT=1, 24 hour clock
    # - date format:                   GD=0, MM/dd/yy
    # - continuous sampling rate:      TH=20, 20 Hz sample rate
    # - anti-alias filter cutoff:      IA=6, 8 Hz cutoff (must be <= 1/2 the sample rate)

    print("\nConfiguring barometers...")
    
    fixedSettingsList = ['VR=Q1.03','XM=1','UN=2','MD=0','XN=0','TS=1','GE=1','TJ=0','TF=.00','TP=0','GT=1','GD=0']
    configurableSettingsList = ['TH=20,P4;>OK','IA=6']

    waitFlag = 1  # barometers should respond, hang on timeout

    for dqPort,dqSN in zip(dqPortList,dqSerialNumberList):
        
        print("\n  configuring serial number: " + dqSN)

        # check fixed barometer settings, quit if not OK
        configErrorFlag = 0
        for configSetting in fixedSettingsList:
            configCmd = '*0100' + configSetting[0:2]
            configResponse = sendCommand(configCmd, dqPort, waitFlag, verbosemodeFlag)
            if configResponse in fixedSettingsList:
                continue
            else:
                print("      " + configResponse + ", NOT OK, want: " + configSetting)
                configErrorFlag = 1
        if configErrorFlag:
            print("    fixed settings:\t\tNOT OK\n")
            print("    Quitting...\n")
            raise(SystemExit)
        print("    fixed settings:\t\tOK")

        # check configurable barometer settings, set if not OK
        for configSetting in configurableSettingsList:
            configCmd = '*0100' + configSetting[0:2]
            configResponse = sendCommand(configCmd, dqPort, waitFlag, verbosemodeFlag)
            if configResponse in configurableSettingsList:
                continue
            else:
                print("      " + configResponse + ", NOT OK, want: " + configSetting)
                configCmd = '*0100EW*0100' + configSetting
                configResponse = sendCommand(configCmd, dqPort, waitFlag, verbosemodeFlag)
                if configResponse in configurableSettingsList:
                    print("      setting change successful")
                else:
                    print("      setting change NOT successful\n")
                    print("    Quitting...\n")
                    raise(SystemExit)
        print("    configurable settings:\tOK")

        # verify the barometer sample rate and anti-alias filter cutoff - sample rate must
        # be at least twice the anti-alias cutoff frequency (Nyquist sampling theorem)
        configCmd = '*0100TH'
        configResponse = sendCommand(configCmd, dqPort, waitFlag, verbosemodeFlag)
        TH = int(configResponse[3:configResponse.find(",")])
        configCmd = '*0100IA'
        configResponse = sendCommand(configCmd, dqPort, waitFlag, verbosemodeFlag)
        IA = int(configResponse[3:])
        if TH >= 2*2**(9-IA):
            print("    sample rate = " + str(TH) + " Hz, anti-alias cutoff = " + str(IA) + " (" + str(2**(9-IA)) + " Hz), OK")
        else:
            print("    sample rate = " + str(TH) + " Hz, anti-alias cutoff = " + str(IA) + " (" + str(2**(9-IA)) + " Hz), NOT OK")
            print("    sample rate must be at least twice the cutoff frequency!")
            print("    Quitting...\n")
            raise(SystemExit)

    #
    # set the barometer clocks to the current computer time
    #
    # since barometer time is stored in volatile memory, I assume this memory can be
    # changed an arbitrary number of times, unlike the non-volatile EPROM that holds
    # the barometer configuration settings
    #
    
    print("\nSetting barometer clocks...")
    
    utcTimeStr = datetime.utcnow().strftime('%m/%d/%y %H:%M:%S')
    for dqPort,dqSN in zip(dqPortList,dqSerialNumberList):
        timeSetCmd = '*0100EW*0100GR=' + utcTimeStr
        timeSetResponse = sendCommand(timeSetCmd, dqPort, waitFlag, verbosemodeFlag)
        print("\n  " + dqSN + ", date/time: " + timeSetResponse[3:])

    #
    # start continuous pressure sampling
    #

    print("\nStarting continuous sampling...")

    # define a readline object for each barometer - because its more efficient,
    # we will use the readline object's readline method to read the serial ports
    # instead of using the pyserial readline method
    dqDeviceList = []
    for dqPort in dqPortList:
        dqDevice = ReadLine(dqPort)
        dqDeviceList.append(dqDevice)

    # set the serial port timeout for each barometer to be larger than the sample period
    dqSampleRate = TH
    dqSamplePeriod = 1/dqSampleRate
#    print("\n  sample rate = " + str(dqSampleRate) + ", sample period = " + str(dqSamplePeriod))
    for dqPort in dqPortList:
        dqPort.timeout = 1.5 * dqSamplePeriod
#        print("port timeout = " + str(dqPort.timeout))

    # initialize current hour to a negative number to force a new log file with first sample
    logFile = None
    currentUTCHour = -1

    # define a failure list for detecting and handling barometer failures
    dqFailuresList = [];
    for dqPort in dqPortList:
        dqFailures = 0;
        dqFailuresList.append(dqFailures)

    # send a P4 command to to each barometer start continuous sampling
    for dqPort in dqPortList:
        sendCommand('*0100P4', dqPort, waitFlag, verbosemodeFlag)

    #
    # sample until user quits, e.g., via cntl-C
    #

    print("\nRunning...quit with ctrl-C...\n")

    try:
    
        while True:
            
            #
            # open a new log file on change in hour of day
            #
            
            if not testmodeFlag:
#                if datetime.utcnow().minute != currentUTCHour:
#                    currentUTCHour = datetime.utcnow().minute
                if datetime.utcnow().hour != currentUTCHour:
                    currentUTCHour = datetime.utcnow().hour
                    if logFile is not None:
                        logFile.close()
                    logDirectoryName = os.path.join(logDir, datetime.utcnow().strftime("DQLOG-%Y%m%d"))
                    os.makedirs(logDirectoryName, exist_ok=True)
                    logFileName = datetime.utcnow().strftime("DQ-%Y%m%d-%H%M%S-"
                                                             + str(dqSampleRate)
                                                             + "-" + str(numBarometers)
                                                             + ".txt")
                    logFilePath = os.path.join(logDirectoryName, logFileName)
                    logFile = open(logFilePath,'w+')
                    print("  opening log file: " + logFilePath + "\n")

            #
            # read and log pressure samples
            #
            # here we use the readline object readline method instead of the pyserial
            # readline method - note also that a barometer is considered failed and
            # is ignored after 3 consecutive timeouts
            #
            
            for dqIndex, dqSN, dqDevice, dqFailures in zip(range(len(dqPortList)), dqSerialNumberList, dqDeviceList, dqFailuresList):
                if dqFailures < 3:
                    binIn = dqDevice.readline()
                    if not binIn:
                        dateStr = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                        print("  " + dqSN + ", TIMEOUT DURING READ AT: " + dateStr + "\n")
                        dqFailures += 1
                        dqFailuresList[dqIndex] = dqFailures
                        if dqFailures >= 3:
                            print("  " + dqSN + ", APPEARS TO HAVE FAILED AT: " + dateStr + "\n")
                        continue
                    dqFailures = 0
                    dqFailuresList[dqIndex] = dqFailures
                    strIn = binIn.decode()
                    if testmodeFlag:
                        print("  " + dqSN + ", " + strIn)
                    else:
                        logFile.write(dqSN + ", " + strIn[7:-2] + "\n")

            #
            # handle barometer failures
            #

            numFailed = np.sum(i >= 3 for i in dqFailuresList)
            if numFailed == numBarometers:
                dateStr = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                print("  ALL BAROMETERS APPEAR TO HAVE FAILED AT: " + dateStr)
                raise(SystemExit)

    except (KeyboardInterrupt, SystemExit):
    
        print("\n\nGot interrupt...\n")
    
    finally:
        
        print("Quitting...\n")
        
        for dqPort in dqPortList:
            # send a command to stop P4 continuous sampling - any command will do
            sendCommand('*0100SN', dqPort, 0, verbosemodeFlag)
            time.sleep(0.2)
            dqPort.close()
        
        if not testmodeFlag:
            logFile.close()

#
# main
#

if __name__ == '__main__':
    main()
