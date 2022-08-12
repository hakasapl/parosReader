#!/bin/bash

apt install -y python3-pip python3-smbus i2c-tools usbmuxd
pip install pika
pip install Adafruit-ADS1x15
pip install pandas
pip install numpy
pip install matplotlib

git_location="/home/pi/parosReader"
chown pi:pi -R $git_location
chmod +x $git_location/src/dqLogger/run.sh
chmod +x $git_location/src/dqLogger/run-mq.sh
chmod +x $git_location/src/voltage_anemometer/run.sh
chmod +x $git_location/src/voltage_anemometer/run-mq.sh

echo "Should we send to rabbitmq (y/n)?"
read rmq

# remove service files if they are already there
if [ "$rmq" = "y" ]; then
    echo "Setting up to also send to rabbitmq..."
    cp $git_location/baro-logger-mq.service /etc/systemd/system/baro-logger.service
    cp $git_location/anim-logger-mq.service /etc/systemd/system/anim-logger.service
else
    echo "Not sending to rabbitmq"
    cp $git_location/baro-logger.service /etc/systemd/system/baro-logger.service
    cp $git_location/anim-logger.service /etc/systemd/system/anim-logger.service
fi

systemctl daemon-reload
systemctl enable baro-logger
systemctl enable anim-logger

mkdir /opt/DQLOG
chown pi:pi /opt/DQLOG

mkdir /opt/ANIMLOG
chown pi:pi /opt/ANIMLOG

echo "Remember to enable I2C bus using raspi-config, and set the hostname. Then you can reboot to begin"
