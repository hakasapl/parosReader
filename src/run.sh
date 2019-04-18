#!/bin/bash
set -x
#nohup ./wxtlogger_t &
cd voltage_anemometer
nohup python ./WindSpeedLogger.py &
#screen -d -m ./voltage_anemometer/WindSpeedLogger.py
cd ..
cd dqLogger
nohup ./dqLogger.py &
cd ..
ps aux | grep python > pid.txt
#screen -d -m ./dqLogger/dqLogger.py
