#!/usr/bin/env python
from datetime import date, timedelta
import os.path
import ftplib
import os

os.chdir("/root/")
myFTP = ftplib.FTP('casa.sharath.pro', 'casa', 'casa2017')
yesterday = date.today() - timedelta(1)
myPath = yesterday.strftime("data-%Y%m%d")


def upload_files(path):
    myFTP.mkd(path)
    myFTP.cwd(path)
    files = os.listdir(path)
    os.chdir(path)
    for f in files:
        fh = open(f, 'rb')
        myFTP.storbinary('STOR ' + f, fh)
        fh.close()
    myFTP.cwd('..')

upload_files(myPath)
myFTP.close()
