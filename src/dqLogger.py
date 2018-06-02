#
#
# dqLogger.py - Python script to log Paroscientific DigiQuartz barometer data
#
#   usage: python dqLogger.py [-h] [-t] [-s SAMPLERATE] [-r LOGROOTDIR]
#
#   D.L. Pepyne
#   Copyright 2018 __University of Massachusetts__. All rights reserved.
#
#   Revision: 19 March 2018; 1 May 2018; 8 May 2018; 9 May 2018
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


#
# method to yield a timer generator
#

def g_tick(period):
    t = time.time()
    count = 0
    while True:
        count += 1
        yield max(t + count*period - time.time(),0)


#
# method to sample and log barometer pressure data
#

def sample_and_log(dqPortList, dqSerialNumberList, dqSampleRate, logRootDir, testmodeFlag):

    global currentUTCHour
    global logFile

    # on change in hour, close current log file and open a new one
    # NOTE - FOR TESTING WE MAKE A NEW FILE EACH MINUTE
    if not testmodeFlag:
        if datetime.utcnow().minute != currentUTCHour:
            currentUTCHour = datetime.utcnow().minute
#        if datetime.utcnow().hour != currentUTCHour:
#            currentUTCHour = datetime.utcnow().hour
            if logFile is not None:
                logFile.close()
            logDirectoryName = os.path.join(logRootDir, datetime.utcnow().strftime("DQLOG-%Y%m%d"))
            os.makedirs(logDirectoryName, exist_ok=True)
            logFileName = datetime.utcnow().strftime("DQ-%Y%m%d-%H%M%S-"
                                                     + str(dqSampleRate) + "-" + str(len(dqPortList)) + ".txt")
            logFilePath = os.path.join(logDirectoryName, logFileName)
            logFile = open(logFilePath,'w+')
            print("  opening log file: " + logFilePath)

    # read and log pressure samples
    for port, dqSN in zip(dqPortList,dqSerialNumberList):
        # read serial port
        binIn = port.readline()
        strIn = binIn.decode()
        # if test mode, print data to console, otherwise write to log file
        if testmodeFlag:
            print("  " + dqSN + ", " + strIn[7:-2])
        else:
            logFile.write(dqSN + ", " + strIn[7:-2] + "\n")


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
    portList = serial.tools.list_ports.comports()
    for element in portList:
        if "usbserial" in element.device:
            usbPortList.append(element.device)
    
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
        dqPort.timeout = 0.10
        dqPort.open()
        strOut = '*0100MN' + '\r\n'                      # request barometer model number
        binOut = strOut.encode()
        dqPort.write(binOut)
        binIn = dqPort.readline()
        strIn = binIn.decode()
        if "6000-16B-IS" in strIn:                       # program assumes a specific model number
            print("    found barometer: " + strIn[:-2])  # don't print carriage return/line feed
            strOut = '*0100SN' + '\r\n'                  # request barometer serial number
            binOut = strOut.encode()
            dqPort.write(binOut)
            binIn = dqPort.readline()
            strIn = binIn.decode()
            print("      serial number: " + strIn[:-2])
            dqPortList.append(dqPort)
            dqSerialNumberList.append(strIn[8:-2])       # store serial number only
        else:
            dqPort.close()

    if dqPortList:
        print("\n  " + str(len(dqPortList)) + " barometer(s) found")
    else:
        print("\n  no 6000-16B-IS barometer(s) found\n")
        print("Quitting\n")
        exit()

    #
    # configure the barometer(s) for infrasound sampling - THIS IS TBD
    #

    print("\nConfiguring barometer(s)...\n")

    for dqPort,dqSN in zip(dqPortList,dqSerialNumberList):
        print("  configuring serial number: " + dqSN)
        # get barometer firmware version
        strOut = '*0100VR' + '\r\n'
        binOut = strOut.encode()
        dqPort.write(binOut)
        binIn = dqPort.readline()
        strIn = binIn.decode()
        print("    firmware version: " + strIn[:-2])
        # need to set time, number of digits, nano-mode, IA value, stuff like that
        # note - only write changes if they are not already set, barometer PROM can
        # only be written a finite number of times

    #
    # sample until user quits, e.g., via cntl-C
    #

    print("\nRunning...quit with ctrl-C...\n")

    try:

        # initialize current hour to negative number to open log file with first sample
        currentUTCHour = -1

        # initialize log file to none so does't try to close a non-existent file on entry
        logFile = None

        # set the sample period
        samplePeriod = 1/dqSampleRate

        # make timer generator
        g = g_tick(samplePeriod)

        # start the sampler
        while True:
            # request the pressure sample(s)
            for dqPort in dqPortList:
                strOut = '*0100P3' + '\r\n'
                binOut = strOut.encode()
                dqPort.write(binOut)
            # wait for timer timeout
            time.sleep(next(g))
            # get and log sample
            sample_and_log(dqPortList, dqSerialNumberList, dqSampleRate, logRootDir, testmodeFlag)

    except (KeyboardInterrupt, SystemExit):

        print("\n\nGot keyboard interrupt...\n")
        
    finally:
        
        print("Quitting...\n")

        for dqPort in dqPortList:
            dqPort.close()

        if not testmodeFlag:
            logFile.close()


#
# main
#

if __name__ == '__main__':
    main()
