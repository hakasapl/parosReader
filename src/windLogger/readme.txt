Steps to install the python library for the ADC and enable i2c on the pi

1. sudo apt-get install -y python-smbus
2. sudo apt-get install -y i2c-tools
3. sudo raspi-config
    -interfacing options
      -(advanced options?)
        -i2c
          -enable
4. sudo reboot
5. sudo i2cdetect -y 1
(6. sudo apt-get install build-essential python-dev)
(7. git clone https://github.com/adafruit/Adafruit_Python_ADS1x15.git)
8. cd Adafruit_Python_ADS1x15
9 python setup.py install
