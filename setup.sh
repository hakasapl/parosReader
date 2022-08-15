#!/bin/bash

# colored output helper functions
NC='\e[0m'
echoGreen() {
    echo -n -e "\e[0;32m$1${NC}"
}
echoYellow() {
    echo -n -e "\e[0;33m$1${NC}"
}
echoRed() {
    echo -n -e "\e[0;31m$1${NC}"
}

# check that we are running as root
if [ "$EUID" -ne 0 ]; then
    echoRed "The setup.sh script must be run as root! Try 'sudo ./setup.sh'\n"
    exit 1
fi

# test internet connection
wget -q --spider http://google.com
if [ $? -ne 0 ]; then
    echoRed "An internet connection is required to run this script! Use 'raspi-config' to connect to WiFi or use USB tethering from a phone.\n"
    exit 1
fi

# set git location
git_location="/home/pi/parosReader"
chown pi:pi -R $git_location

# enable i2c bus on taspberry pi
echoGreen "Enabling I2C Bus...\n"
raspi-config nonint do_i2c 0
if [ $? -ne 0 ]; then
    echoRed "Unable to enable I2C bus\n"
    exit 1
fi

# installing apt prerequisites
echoGreen "Installing APT Prerequisites...\n"
apt-get update
apt-get install -y python3-pip python3-smbus i2c-tools usbmuxd libatlas-base-dev gpsd gpsd-tools
if [ $? -ne 0 ]; then
    echoRed "Error installing apt packages\n"
    exit 1
fi

# installing pypi prerequisites
echoGreen "Installing Python Packages...\n"
pip install pika Adafruit-ADS1x15 pySerial
if [ $? -ne 0 ]; then
    echoRed "Error installing PyPI packages\n"
    exit 1
fi

echoYellow "How many barometers are in this module (def: 2)? "
read num_baro
num_baro=${num_baro:-2}

echoYellow "Where should we output barometer logs (def: /opt/DQLOG)? "
read baro_log_loc
baro_log_loc=${baro_log_loc:-/opt/DQLOG}

echoYellow "Where should we output wind speed logs (def: /opt/WINDLOG)? "
read baro_wind_loc
wind_log_loc=${baro_wind_loc:-/opt/WINDLOG}

# create cmd strings
baro_cmd="python3 ${git_location}/src/dqLogger/dqLogger.py -d ${baro_log_loc} -n ${num_baro}"
wind_cmd="python3 ${git_location}/src/voltage_anemometer/WindSpeedLogger.py -d ${wind_log_loc}"

# password prompt function
getRmqPass() {
    echoYellow "What is the password of the remote rabbitmq server? "
    read -s rmq_pass
    echo ""

    echoYellow "Confirm the password of the remote rabbitmq server: "
    read -s rmq_pass_confirm
    echo ""

    if [ "$rmq_pass" != "$rmq_pass_confirm" ]; then
        echoRed "Passwords do not match, try again\n"
        getRmqPass
    fi
}

# check if rmq posting is required
echoYellow "Should we send to rabbitmq in addition to local logging (y/n)? "
read rmq
mq_cmd=""
if [ "$rmq" = "y" ]; then
    echoYellow "What is the hostname of the remote rabbitmq server? "
    read rmq_host

    echoYellow "What is the username of the remote rabbitmq server? "
    read rmq_user

    getRmqPass

    mq_cmd=" -i ${rmq_host} -u ${rmq_user} -p ${rmq_pass}"
fi

# create run files
echoGreen "Creating run files for barometer logging...\n"
echo "#!/bin/bash" > $git_location/run/baro.sh
echo "${baro_cmd}${mq_cmd}" >> $git_location/run/baro.sh
chmod +x $git_location/run/baro.sh

echoGreen "Creating run files for wind speed logging...\n"
echo "#!/bin/bash" > $git_location/run/wind.sh
echo "${wind_cmd}${mq_cmd}" >> $git_location/run/wind.sh
chmod +x $git_location/run/wind.sh

# deploy service files
echoGreen "Deploying systemd service files...\n"
cp $git_location/services/baro-logger.service /etc/systemd/system/baro-logger.service
cp $git_location/services/wind-logger.service /etc/systemd/system/wind-logger.service
systemctl daemon-reload

# creating logging directories
echoGreen "Creating barometer log directory...\n"
mkdir -p $baro_log_loc
chown pi:pi $baro_log_loc

echoGreen "Creating wind speed log directory...\n"
mkdir -p $wind_log_loc
chown pi:pi $wind_log_loc

echoGreen "Should logging be autostarted on boot (y/n)? "
read enable_logger
if [ "$enable_logger" = "y" ]; then
    systemctl enable baro-logger
    systemctl enable wind-logger
else
    systemctl disable baro-logger
    systemctl disable wind-logger
fi

echoGreen "Should we start logging now (y/n)? "
read start_logger
if [ "$start_logger" = "y" ]; then
    systemctl start baro-logger
    systemctl start wind-logger
else
    systemctl stop baro-logger
    systemctl stop wind-logger
fi

printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
echo "Setup script complete!"
echo ""
echo "For barometer logging control, use 'systemctl start baro-logger' or 'systemctl stop baro-logger'"
echo "To view logs for baro-logger, use 'journalctl -eu baro-logger'"
echo ""
echo "For wind speed logging control, use 'systemctl start wind-logger' or 'systemctl stop wind-logger'"
echo "To view logs for wind-logger, use 'journalctl -eu wind-logger'"
echo ""
echo "You can rerun this script anytime to change parameters of the deployment"
printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -