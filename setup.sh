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
if [[ "$*" == *"--skip-apt"* ]]; then
    echoGreen "Skipping installing APT prerequisites\n"
else
    echoGreen "Installing APT Prerequisites...\n"
    apt-get update
    apt-get install -y python3-pip python3-smbus i2c-tools usbmuxd libatlas-base-dev
    if [ $? -ne 0 ]; then
        echoRed "Error installing apt packages\n"
        exit 1
    fi
fi

# installing pypi prerequisites
if [[ "$*" == *"--skip-pip"* ]]; then
    echoGreen "Skipping installing Python packages\n"
else
    echoGreen "Installing Python Packages...\n"
    pip install pySerial pandas
    if [ $? -ne 0 ]; then
        echoRed "Error installing PyPI packages\n"
        exit 1
    fi
fi

echoYellow "Does the box have a barometer (y/n)? "
read baro
if [ "$baro" = "y" ]; then
    echoYellow "How many barometers are in this module (def: 2)? "
    read num_baro
    num_baro=${num_baro:-2}

    echoYellow "Where should we output barometer logs (def: /opt/BAROLOG)? "
    read baro_log_loc
    baro_log_loc=${baro_log_loc:-/opt/BAROLOG}

    baro_cmd="python3 ${git_location}/src/baroLogger/baroLogger.py -d ${baro_log_loc} -n ${num_baro}"

    echoGreen "Creating run files for barometer logging...\n"
    echo "#!/bin/bash" > $git_location/run/baro.sh
    echo "${baro_cmd}" >> $git_location/run/baro.sh
    chmod +x $git_location/run/baro.sh

    # deploy service files
    echoGreen "Deploying systemd service files for barometer...\n"
    cp $git_location/services/baro-logger.service /etc/systemd/system/baro-logger.service
    systemctl daemon-reload
    systemctl enable baro-logger

    # creating logging directories
    echoGreen "Creating barometer log directory...\n"
    mkdir -p $baro_log_loc
    chown pi:pi $baro_log_loc
fi

echoYellow "Does the box have an anemometer (y/n)? "
read anemometer
if [ "$anemometer" = "y" ]; then
    echoYellow "Where should we output wind speed logs (def: /opt/WINDLOG)? "
    read baro_wind_loc
    wind_log_loc=${baro_wind_loc:-/opt/WINDLOG}

    wind_cmd="python3 ${git_location}/src/windLogger/windLogger.py -d ${wind_log_loc}"

    echoGreen "Creating run files for wind speed logging...\n"
    echo "#!/bin/bash" > $git_location/run/wind.sh
    echo "${wind_cmd}" >> $git_location/run/wind.sh
    chmod +x $git_location/run/wind.sh

    # deploy service files
    echoGreen "Deploying systemd service files for anemometer...\n"
    cp $git_location/services/wind-logger.service /etc/systemd/system/wind-logger.service
    systemctl daemon-reload
    systemctl enable wind-logger

    echoGreen "Creating wind speed log directory...\n"
    mkdir -p $wind_log_loc
    chown pi:pi $wind_log_loc
fi

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

    influxdb_cmd="${influxdb_hostname} ${influxdb_org} ${influxdb_token} ${influxdb_bucket}"
    
    if [ "$baro" = "y" ]; then
        influxdb_cmd="$influxdb_cmd -l ${baro_log_loc}"
    fi

    if [ "$anemometer" = "y" ]; then
        influxdb_cmd="$influxdb_cmd -l ${wind_log_loc}"
    fi

    echoGreen "[INFLUXDB] Creating run files for influxdb dataSender...\n"
    echo "#!/bin/bash" > $git_location/run/datasender.sh
    echo "${datasender_cmd} ${influxdb_cmd}" >> $git_location/run/datasender.sh
    chmod +x $git_location/run/datasender.sh

    echoGreen "[INFLUXDB] Deploying systemd service files...\n"
    cp $git_location/services/datasender* /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable datasender.timer
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
