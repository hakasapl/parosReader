# parosReader
Repository for the CASA Infrasound Lab

# Dependencies
* git

```
apt update
apt install git
```

# Installing the Code
You can installl the scripts with:
```
cd ~
git clone https://github.com/UmassCASA/parosReader.git
cd parosReader
chmod +x setup.sh
sudo ./setup.sh
```

# Running the Program
Baro logger is enabled by default as a systemd service. Check on its status with `systemctl status baro-logger`  
Wind logger is enabled by default as a systemd service. Check on its status with `systemctl status wind-logger`
