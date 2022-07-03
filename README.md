# parosReader
Repository for the CASA Infrasound Lab

# Dependencies
* git

```
apt-get update
apt-get install git
```

# Installing the Code
You can installl the scripts with:
```
git clone https://github.com/UmassCASA/parosReader.git
cd parosreader/src
chmod +x run.sh
```

# Running the Program
We like to run with nohup just in case:
```
 nohup ./run.sh 
```

Also maybe delete the old nohup.out file first (no worries, it will append to the end if you don't).

# Autorun on reboot
In the src directory there is a crontab.txt file that is installed on the pi to automatically restart the
barometer data logger and anemomemter data logger when it boots up.

