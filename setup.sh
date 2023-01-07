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

# enable SPI bus on taspberry pi
echoGreen "Enabling SPI Bus...\n"
raspi-config nonint do_spi 0
if [ $? -ne 0 ]; then
    echoRed "Unable to enable SPI bus\n"
    exit 1
fi

# installing apt prerequisites
echoGreen "Installing APT Prerequisites...\n"
apt-get update
apt-get install -y python3-pip python3-smbus i2c-tools usbmuxd libatlas-base-dev gpsd gpsd-tools ntp
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

# setup GPS NTP source
echoYellow "Does this box have a GPS (y/n)? "
read gps_enable
if [ "$gps_enable" == "y" ]; then
    echoGreen "Setting up GPS...\n"
    grep -qxF 'GPS_BAUD=9600' /etc/default/gpsd || echo 'GPS_BAUD=9600' >> /etc/default/gpsd

    systemctl enable gpsd.socket
    systemctl start gpsd.socket
    systemctl enable gpsd
    systemctl start gpsd

    grep -qxF 'server 127.127.20.0 mode 16 minpoll 4 prefer' /etc/ntp.conf || echo 'server 127.127.20.0 mode 16 minpoll 4 prefer' >> /etc/ntp.conf
    grep -qxF 'fudge 127.127.20.0 flag3 1 flag2 0 time1 0.0' /etc/ntp.conf || echo 'fudge 127.127.20.0 flag3 1 flag2 0 time1 0.0' >> /etc/ntp.conf

    grep -qxF 'server 127.127.20.1 mode 16 minpoll 4 prefer' /etc/ntp.conf || echo 'server 127.127.20.1 mode 16 minpoll 4 prefer' >> /etc/ntp.conf
    grep -qxF 'fudge 127.127.20.1 flag3 1 flag2 0 time1 0.0' /etc/ntp.conf || echo 'fudge 127.127.20.1 flag3 1 flag2 0 time1 0.0' >> /etc/ntp.conf

    grep -qxF 'server 127.127.20.2 mode 16 minpoll 4 prefer' /etc/ntp.conf || echo 'server 127.127.20.2 mode 16 minpoll 4 prefer' >> /etc/ntp.conf
    grep -qxF 'fudge 127.127.20.2 flag3 1 flag2 0 time1 0.0' /etc/ntp.conf || echo 'fudge 127.127.20.2 flag3 1 flag2 0 time1 0.0' >> /etc/ntp.conf

    grep -qxF 'server 127.127.20.3 mode 16 minpoll 4 prefer' /etc/ntp.conf || echo 'server 127.127.20.3 mode 16 minpoll 4 prefer' >> /etc/ntp.conf
    grep -qxF 'fudge 127.127.20.3 flag3 1 flag2 0 time1 0.0' /etc/ntp.conf || echo 'fudge 127.127.20.3 flag3 1 flag2 0 time1 0.0' >> /etc/ntp.conf

    grep -qxF 'server 127.127.20.4 mode 16 minpoll 4 prefer' /etc/ntp.conf || echo 'server 127.127.20.4 mode 16 minpoll 4 prefer' >> /etc/ntp.conf
    grep -qxF 'fudge 127.127.20.4 flag3 1 flag2 0 time1 0.0' /etc/ntp.conf || echo 'fudge 127.127.20.4 flag3 1 flag2 0 time1 0.0' >> /etc/ntp.conf

    grep -qxF 'server 127.127.20.5 mode 16 minpoll 4 prefer' /etc/ntp.conf || echo 'server 127.127.20.5 mode 16 minpoll 4 prefer' >> /etc/ntp.conf
    grep -qxF 'fudge 127.127.20.5 flag3 1 flag2 0 time1 0.0' /etc/ntp.conf || echo 'fudge 127.127.20.5 flag3 1 flag2 0 time1 0.0' >> /etc/ntp.conf

    systemctl restart ntp
fi

echoYellow "How many barometers are in this module (def: 2)? "
read num_baro
num_baro=${num_baro:-2}

echoYellow "Where should we output barometer logs (def: /opt/BAROLOG)? "
read baro_log_loc
baro_log_loc=${baro_log_loc:-/opt/BAROLOG}

echoYellow "Where should we output wind speed logs (def: /opt/WINDLOG)? "
read baro_wind_loc
wind_log_loc=${baro_wind_loc:-/opt/WINDLOG}

# create cmd strings
baro_cmd="python3 ${git_location}/src/baroLogger/baroLogger.py -d ${baro_log_loc} -n ${num_baro}"
wind_cmd="python3 ${git_location}/src/windLogger/windLogger.py -d ${wind_log_loc}"

# check if influxdb posting is required
echoYellow "Should data be uploaded to influxdb (y/n)? "
read influxdb
if [ "$influxdb" = "y" ]; then
    datasender_cmd="python3 ${git_location}/src/dataSender/dataSender.py"

    echoYellow "[INFLUXDB] What is the hostname? "
    read influxdb_hostname

    echoYellow "[INFLUXDB] What is the organization? "
    read influxdb_org

    echoYellow "[INFLUXDB] What is the bucket? "
    read influxdb_bucket

    echoYellow "[INFLUXDB] What is the API token? "
    read influxdb_token

    influxdb_cmd="${influxdb_url} ${influxdb_org} ${influxdb_token} ${influxdb_bucket} -l ${baro_log_loc} -l ${wind_log_loc}"

    echoGreen "[INFLUXDB] Creating run files for influxdb dataSender...\n"
    echo "#!/bin/bash" > $git_location/run/datasender.sh
    echo "${datasender_cmd} ${influxdb_cmd}" >> $git_location/run/datasender.sh
    chmod +x $git_location/run/datasender.sh

    echoGreen "[INFLUXDB] Deploying systemd service files...\n"
    cp $git_location/services/datasender* /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable datasender.timer
fi

# create run files
echoGreen "Creating run files for barometer logging...\n"
echo "#!/bin/bash" > $git_location/run/baro.sh
echo "${baro_cmd}" >> $git_location/run/baro.sh
chmod +x $git_location/run/baro.sh

echoGreen "Creating run files for wind speed logging...\n"
echo "#!/bin/bash" > $git_location/run/wind.sh
echo "${wind_cmd}" >> $git_location/run/wind.sh
chmod +x $git_location/run/wind.sh

# deploy service files
echoGreen "Deploying systemd service files...\n"
cp $git_location/services/baro-logger.service /etc/systemd/system/baro-logger.service
cp $git_location/services/wind-logger.service /etc/systemd/system/wind-logger.service
systemctl daemon-reload
systemctl enable baro-logger
systemctl enable wind-logger

# creating logging directories
echoGreen "Creating barometer log directory...\n"
mkdir -p $baro_log_loc
chown pi:pi $baro_log_loc

echoGreen "Creating wind speed log directory...\n"
mkdir -p $wind_log_loc
chown pi:pi $wind_log_loc

echoYellow "Should this box forward SSH to NGROK (y/n)? "
read ngrok_enable
if [ "$ngrok_enable" = "y" ]; then
    echoYellow "Enter ngrok authentication token: "
    read ngrok_token

    mkdir -p /home/pi/.config/ngrok
    echo 'version: "2"' > /home/pi/.config/ngrok/ngrok.yml
    echo "authtoken: $ngrok_token" >> /home/pi/.config/ngrok/ngrok.yml
    cp $git_location/services/ngrok.service /etc/systemd/system/ngrok.service
    systemctl daemon-reload
    systemctl enable ngrok
    systemctl restart ngrok
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
echo "If this is the first time this script was run, you'll need to reboot"
printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
