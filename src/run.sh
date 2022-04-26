#!/bin/bash
cd /home/pi/parosReader/src
cd voltage_anemometer
python ./WindSpeedLogger.py &
cd ..
cd dqLogger
./dqLogger.py &
cd ..
ps aux | grep python > pid.txt
