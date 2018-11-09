#!/bin/bash
#nohup ./wxtlogger_t &
screen -d -m ./wxtlogger_t
#nohup ./dqLogger/dqLogger.py &
screen -d -m ./dqLogger/dqLogger.py
