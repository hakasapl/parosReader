#!/usr/bin/env python3
#
# dqLoggerP4.py - Python script to log Paroscientific DigiQuartz barometer data
#               - This one uses P4 continuous sampling
#
#   usage: ./dqLoggerP4.py [-h] [-t] [-v] [-s SAMPLERATE] [-r LOGROOTDIR]
#
#   Westy based on code by D.L. Pepyne
#   Copyright 2018 __University of Massachusetts__. All rights reserved.
#
#   Revision: 19 March 2018; 1 May 2018; 8 May 2018; 9 May 2018; 12 May 2018
#
# TO DO:
#   - DONE - close file when reaches certain size, or on date change
#   - DONE - sample rate should be a user input with a default value
#   - DONE - put log files in directory named: DQLOG-YYYYmmdd
#   - DONE - instead of -v printing AND saving, use -t for test, which prints but does not save
#   - DONE - allow a logRootDir, e.g., so data can be stored on a usb drive
#   - DONE - understand what happens when barometer loses power or connection is lost while
#            logger is running - works ok, but barometer time gets reset when you plug it back in
#   - DONE - restructure code so things like sampling and opening log files are only done once
#   - DONE - check the timing, particularly for high sample rates - seems OK - 40 Hz gives
#            40 samples per second
#   - do a long run to make sure program doesn't crash and properly makes log files
#   - need to figure out how we want to configure the barometers for infrasound sampling
#   - need the command that prints the complete barometer configuration
#
#


import time
import serial
import serial.tools.list_ports
import sys
import os
import argparse
import datetime
from datetime import datetime

def sendCommand(strOut, dqPort, verbosemodeFlag):
    if verbosemodeFlag:
        print("    command: " + strOut)
    strOut = strOut + '\r\n'
    binOut = strOut.encode()
    dqPort.write(binOut)
    binIn = dqPort.readline()
    strIn = binIn.decode()
    if verbosemodeFlag:
        print("    response: " + strIn[:-2])
    return strIn[8:-2]

#
# main method
#

def main():

    global currentUTCHour
    global logFile
    
    #
    # define program defaults
    #

    DEFAULT_SAMPLERATE = 10

    #
    # define parser for user input arguments
    #

    parser = argparse.ArgumentParser(description='Logs regularly sampled barometer pressure data. Assumes Model 6000-16B-IS Paroscientific DigiQuartz barometers.')
    parser.add_argument("-t", "--test",
                        help="print barometer data to console rather than saving to log file for testing",
                        action="store_true")
    parser.add_argument("-v", "--verbose",
                        help="show verbose output",
                        action="store_true")
    parser.add_argument("-s", "--samplerate",
                        type=int,
                        default=DEFAULT_SAMPLERATE,
                        help="set barometer sample rate in Hz (default = 20 Hz)")
    parser.add_argument("-r", "--logRootDir",
                        type=str,
                        action="store",
                        default="./",
                        help="root data directory, use \"\" around names with white space (default = ./)")

    #
    # parse user input arguments
    #

    args = parser.parse_args()

    print("\nParsing user inputs...\n")

    if args.test:
        testmodeFlag = 1
    else:
        testmodeFlag = 0

    if args.verbose:
        verbosemodeFlag = 1
    else:
        verbosemodeFlag = 0

    dqSampleRate = int(args.samplerate)

    if (not dqSampleRate > 0 or dqSampleRate > 45):
        print("  sample rate must be an integer between 1 and 45 Hz\n")
        print("Quitting\n")
        exit()

    logRootDir = args.logRootDir

    if not os.path.isdir(logRootDir):
        print("  log root directory \"" + logRootDir + "\" does not exist\n")
        print("Quitting\n")
        exit()

    if testmodeFlag:
        print("  test mode   = TRUE")
    else:
        print("  test mode   = FALSE")

    print("  sample rate = " + str(args.samplerate) + " Hz")

    print("  log root directory = " + logRootDir)

    #
    # get list of usbserial ports
    #
    
    print("\nChecking for usbserial ports...\n")

    usbPortList = []
    # For Raspberry PI
    if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        portList = glob.glob('/dev/tty[A-Za-z]*')
        for port in portList:
            if "USB" in port:
                usbPortList.append(port)
    # For OSX
    elif sys.platform.startswith('darwin'):
        portList = serial.tools.list_ports.comports()
        for element in portList:
            if "usbserial" in element.device:
                usbPortList.append(element.device)
    else:
        raise EnvironmentError('Unsupported platform')
    
    #
    # print list of usbserial ports, quit if none
    #

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
        dqPort.timeout = 0.1
        dqPort.open()

        modelNumberResponse = sendCommand('*0100MN', dqPort, verbosemodeFlag)
        if verbosemodeFlag:
            print("    modelNumberResponse" + modelNumberResponse)
        if "6000-16B-IS" in modelNumberResponse:                       # program assumes a specific model number
            print("    barometer response: " + modelNumberResponse) 
            serialNumberResponse = sendCommand('*0100SN', dqPort, verbosemodeFlag)
            print("      serial number response: " + serialNumberResponse)
            dqPortList.append(dqPort)
            dqSerialNumberList.append(serialNumberResponse)       # store serial number only
        else:
            if verbosemodeFlag:
                print("    bad barometer response: " + modelNumberResponse)
            dqPort.close()

    if dqPortList:
        print("\n  " + str(len(dqPortList)) + " barometer(s) found")
    else:
        print("\n  no 6000-16B-IS barometer(s) found\n")
        print("Quitting\n")
        exit()

    #
    # configure the barometer(s) for infrasound sampling
    # want:
    # UN=2 - hPa
    # XM=1 - nano-resolution mode
    # MD=0
    # TH=dqSampleRate
    # IA=int( ceil( log2(128/dqSampleRate) + 3 ) ) - see Table 6.1
    # XN=0
    #
    # need to set time, number of digits, nano-mode, IA value, stuff like that
    # note - only write changes if they are not already set, barometer PROM can
    # only be written a finite number of times

    print("\nConfiguring barometer(s)...")

    for dqPort,dqSN in zip(dqPortList,dqSerialNumberList):
        print("\n  configuring serial number: " + dqSN + "\n")
        # get barometer firmware version
        print("    firmware version: " + sendCommand('*0100VR', dqPort, verbosemodeFlag))
        time.sleep(0.1)
        # get nano-resolution mode
        nanoresolutionMode = sendCommand('*0100XM', dqPort, verbosemodeFlag)
        if (nanoresolutionMode == "1"):
            print("    nano-resolution mode: " + nanoresolutionMode + " (enabled)")
        else:
            print("    nano-resolution mode: " + nanoresolutionMode + " (disabled)")
        time.sleep(0.1)
        # get pressure units
        print("    pressure units: " + sendCommand('*0100UN', dqPort, verbosemodeFlag))
        time.sleep(0.1)
        # get data output mode
        print("    data output mode: " + sendCommand('*0100MD', dqPort, verbosemodeFlag))
        time.sleep(0.1)
        # get number of significant digits
        print("    significant digits: " + sendCommand('*0100XN', dqPort, verbosemodeFlag))
        time.sleep(0.1)
        # get the sample rate
        print("    sample rate: " + sendCommand('*0100TH', dqPort, verbosemodeFlag))
        time.sleep(0.1)
        # get anti-alias filter cutoff value
        print("    anti-alias filter cutoff value: " + sendCommand('*0100IA', dqPort, verbosemodeFlag))
        time.sleep(0.1)
        # get current date and time
        print("    current date and time: " + sendCommand('*0100GR', dqPort, verbosemodeFlag))



    #
    # initialize current hour (negative number opens log with first sample) and log file (to
    # none so its defined as a global)
    #

    currentUTCHour = -1
    logFile = None

    #
    # start continuous sampling
    #

    for dqPort in dqPortList:
        sendCommand('*0100P4', dqPort, verbosemodeFlag)

    # wait for sampling to start
    for dqPort in dqPortList:
        while True:
            binIn = dqPort.readline()
            if not binIn:
                if verbosemodeFlag:
                    print("\n" + dqSN + ", WAITING FOR DATA\n")
            else:
                strIn = binIn.decode()
                if verbosemodeFlag:
                    print(strIn)
                break

    #
    # sample until user quits, e.g., via cntl-C
    #

    print("\nRunning...quit with ctrl-C...\n")



    try:
        
        while True:
        
            # on change in hour, open new log file
            if not testmodeFlag:
                #        if datetime.utcnow().minute != currentUTCHour:
                #            currentUTCHour = datetime.utcnow().minute
                if datetime.utcnow().hour != currentUTCHour:
                    currentUTCHour = datetime.utcnow().hour
                    if logFile is not None:
                        logFile.close()
                    logDirectoryName = os.path.join(logRootDir, datetime.utcnow().strftime("DQLOG-%Y%m%d"))
                    os.makedirs(logDirectoryName, exist_ok=True)
                    logFileName = datetime.utcnow().strftime("DQ-%Y%m%d-%H%M%S-"
                                                             + str(dqSampleRate)
                                                             + "-" + str(len(dqPortList))
                                                             + ".txt")
                    logFilePath = os.path.join(logDirectoryName, logFileName)
                    logFile = open(logFilePath,'w+')
                    print("  opening log file: " + logFilePath)
                        
            # read and log the data from each serial port
            for dqPort, dqSN in zip(dqPortList,dqSerialNumberList):
                data = []
                while True:
                    binIn = dqPort.readline()
                    if not binIn:
                        print(dqSN + ", NO DATA\n")
                        # assume power loss, and try to restart continuous sampling
                        sendCommand('*0100P4', dqPort, verbosemodeFlag)
                        break
                    strIn = binIn.decode()
                    if testmodeFlag:
                         print(dqSN + ", " + strIn)
                    else:
                         logFile.write(dqSN + ", " + strIn[7:-2] + "\n")
                    #print(dqSN + ", " + strIn)
                    break

    except (KeyboardInterrupt, SystemExit):

        print("\n\nGot keyboard interrupt...\n")
        
    finally:
        
        print("Quitting...\n")

        for dqPort in dqPortList:
            # send a command to stop P4 continuous sampling
            sendCommand('*0100SN', dqPort, verbosemodeFlag)
            time.sleep(0.1)
            # close the serial port
            dqPort.close()

        if not testmodeFlag:
            logFile.close()


#
# main
#

if __name__ == '__main__':
    main()
