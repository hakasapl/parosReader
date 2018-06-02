#!/usr/bin/env python3
#
# dqLoggerP4.py - Python script to log Paroscientific DigiQuartz barometer data
#               - This one uses P4 continuous sampling
#
#   usage: python dqLoggerP4.py [-h] [-t] [-s SAMPLERATE] [-r LOGROOTDIR]
#
#   D.L. Pepyne
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
#        if datetime.utcnow().minute != currentUTCHour:
#            currentUTCHour = datetime.utcnow().minute
        if datetime.utcnow().hour != currentUTCHour:
            currentUTCHour = datetime.utcnow().hour
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
        dqPort.timeout = 0.1
        dqPort.open()
        strOut = '*0100MN' + '\r\n'                      # request barometer model number
        binOut = strOut.encode()
        dqPort.write(binOut)
        binIn = dqPort.readline()
        strIn = binIn.decode()
        if "6000-16B-IS" in strIn:                       # program assumes a specific model number
            print("    barometer response: " + strIn[:-2])  # don't print carriage return/line feed
            strOut = '*0100SN' + '\r\n'                  # request barometer serial number
            binOut = strOut.encode()
            dqPort.write(binOut)
            binIn = dqPort.readline()
            strIn = binIn.decode()
            print("      serial number response: " + strIn[:-2])
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
        strOut = '*0100VR' + '\r\n'
        binOut = strOut.encode()
        dqPort.write(binOut)
        binIn = dqPort.readline()
        strIn = binIn.decode()
        print("    firmware version: " + strIn[:-2])
        time.sleep(0.1)
        
        # get nano-resolution mode
        strOut = '*0100XM' + '\r\n'
        binOut = strOut.encode()
        dqPort.write(binOut)
        binIn = dqPort.readline()
        strIn = binIn.decode()
        print("    nano-resolution mode response: " + strIn[:-2])
        if (strIn[8:-2] == "1"):
            print("    nano-resolution mode enabled")
        else:
            print("    nano-resolution mode disabled")
        time.sleep(0.1)

        # get pressure units
        strOut = '*0100UN' + '\r\n'
        binOut = strOut.encode()
        dqPort.write(binOut)
        binIn = dqPort.readline()
        strIn = binIn.decode()
        print("    pressure units: " + strIn[:-2])
        time.sleep(0.1)

        # get data output mode
        strOut = '*0100MD' + '\r\n'
        binOut = strOut.encode()
        dqPort.write(binOut)
        binIn = dqPort.readline()
        strIn = binIn.decode()
        print("    data output mode: " + strIn[:-2])
        time.sleep(0.1)
        
        # get number of significant digits
        strOut = '*0100XN' + '\r\n'
        binOut = strOut.encode()
        dqPort.write(binOut)
        binIn = dqPort.readline()
        strIn = binIn.decode()
        print("    significant digits: " + strIn[:-2])
        time.sleep(0.1)

        # get the sample rate
        strOut = '*0100TH' + '\r\n'
        binOut = strOut.encode()
        dqPort.write(binOut)
        binIn = dqPort.readline()
        strIn = binIn.decode()
        print("    sample rate: " + strIn[:-2])
        time.sleep(0.1)

        # get anti-alias filter cutoff value
        strOut = '*0100IA' + '\r\n'
        binOut = strOut.encode()
        dqPort.write(binOut)
        binIn = dqPort.readline()
        strIn = binIn.decode()
        print("    anti-alias filter cutoff value: " + strIn[:-2])
        time.sleep(0.1)

        # get current date and time
        strOut = '*0100GR' + '\r\n'
        binOut = strOut.encode()
        dqPort.write(binOut)
        binIn = dqPort.readline()
        strIn = binIn.decode()
        print("    current date and time: " + strIn[:-2])

#    # TESTING - close serial ports and exit
#    for dqPort in dqPortList:
#        dqPort.close()
#
#    exit()

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
        strOut = '*0100P4' + '\r\n'
        binOut = strOut.encode()
        dqPort.write(binOut)

    # wait for sampling to start
    for dqPort in dqPortList:
        while True:
            binIn = dqPort.readline()
            if not binIn:
                print("\n" + dqSN + ", WAITING FOR DATA\n")
            else:
                strIn = binIn.decode()
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
                        strOut = '*0100P4' + '\r\n'
                        binOut = strOut.encode()
                        dqPort.write(binOut)
                        break
                    strIn = binIn.decode()
                    if testmodeFlag:
                         print(dqSN + ", " + strIn)
                    else:
                         logFile.write(dqSN + ", " + strIn[7:-2] + "\n")
                    #print(dqSN + ", " + strIn)
                    break



#                    ch = dqPort.read(1)
#                    if len(ch) == 0:
#                        print("nada\n")
#                        # rec'd nothing print all
#                        if len(data) > 0:
#                            s = ''
#                            for x in data:
#                                s += ' %02X' % ord(x)
##                            print '%s [len = %d]' % (s, len(data))
#                            print(s + "[len = " + len(data) + "\n")
#                        data = []
#                    else:
#                        print("hi\n")
#                        data.append(ch)

            
#            for dqPort, dqSN in zip(dqPortList,dqSerialNumberList):
#                dqData = []
#                while True:
##                    ch = dqPort.read(1)
#                    binIn = dqPort.readline()
#                    strIn = binIn.decode()
##                    print("Character: " + str(ch) + "\n")
#                    print("String: " + strIn + "\n")
##                    if len(ch) == 0:
#                    if '\r\n' in strIn:
##                    if len(strIn) == 0:
#                        if len(dqData) > 0:
#                            print("SN = " + dqSN + ", Data = " + dqData + "\n")
#                        else:
#                            print("SN = " + dqSN + ", NO DATA" + "\n")
#                        break  # break the innermost while loop
#                    else:
##                        dqData.append(str(ch))
#                        dqData.append(strIn)


                
                


        # STEP 4 - while true to loop forever
        #   a - check for change in current hour
        #       -- open new log file
        #   b - for each serial port
        #       -- clear data variable
        #       -- while true to loop until break
        #         -- read serial port
        #         -- if read returned empty
        #           -- if have data, or if have valid data
        #             -- store serial number and data in log file
        #           -- break out of while loop
        #         -- else
        #           -- append serial data to data variable

#        # initialize current hour to negative number to open log file with first sample
#        currentUTCHour = -1
#
#        # initialize log file to none so does't try to close a non-existent file on entry
#        logFile = None
#
#        # set the sample period
#        samplePeriod = 1/dqSampleRate
#
#        # make timer generator
#        g = g_tick(samplePeriod)
#
#        # start the sampler
#        while True:
#            # request the pressure sample(s)
#            for dqPort in dqPortList:
#                strOut = '*0100P3' + '\r\n'
#                binOut = strOut.encode()
#                dqPort.write(binOut)
#            # wait for timer timeout
#            time.sleep(next(g))
#            # get and log sample
#            sample_and_log(dqPortList, dqSerialNumberList, dqSampleRate, logRootDir, testmodeFlag)

    except (KeyboardInterrupt, SystemExit):

        print("\n\nGot keyboard interrupt...\n")
        
    finally:
        
        print("Quitting...\n")

        for dqPort in dqPortList:
            # send a command to stop P4 continuous sampling
            strOut = '*0100SN' + '\r\n'
            binOut = strOut.encode()
            dqPort.write(binOut)
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
