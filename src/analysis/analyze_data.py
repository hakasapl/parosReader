import argparse
from cProfile import label
import os
import datetime
from time import strftime
from xmlrpc.client import Boolean
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter, detrend, welch, spectrogram
from scipy.signal.windows import hamming
import numpy as np
from obspy.signal.util import next_pow_2

def main():
    now = datetime.datetime.now()

    parser = argparse.ArgumentParser()
    parser.add_argument("data", help="Location of data output", type=str, default="data")
    parser.add_argument("-s", "--start-time", help="Location of output data", type=str, default="1970-01-01-00-00-00")
    parser.add_argument("-e", "--end-time", help="Period, in ms, between each data push", type=str, default=now.strftime("%Y-%m-%d-%H-%M-%S"))
    parser.add_argument("-b", "--block-size", help="Spectrogram block size, in seconds", type=int, default=3600)
    parser.add_argument("--filter-wind", help="Enable wind filter", type=bool, default=False)
    args = parser.parse_args()

    start_time = datetime.datetime.strptime(args.start_time, '%Y-%m-%d-%H-%M-%S')
    end_time = datetime.datetime.strptime(args.end_time, '%Y-%m-%d-%H-%M-%S')

    if start_time > end_time:
        print("End time must be after start time!")
        exit(1)

    data_files = os.listdir(args.data)
    num_files = len(data_files)

    scan_files = []

    for file in data_files:
        # get timestamp of file
        filename = os.path.splitext(file)[0]
        file_parts = filename.split("-")
        if file_parts[0] == "DQ":
            # found DQ log
            print("Found DQ Log: " + file)

        timestamp_str = "-".join(file_parts[1:3])
        timestamp = datetime.datetime.strptime(timestamp_str, '%Y%m%d-%H%M%S')

        # find files that need to be scanned for data
        if timestamp < start_time:
            scan_files.clear()
        
        if timestamp <= end_time:
            scan_files.append(file)
        else:
            break

    imported_data = []
    field_names = ['device_id', 'timestamp', 'value']
    for file in scan_files:
        # scan files
        imported_data.append(pd.read_csv(args.data + "/" + file, names=field_names))

    df = pd.concat(imported_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'], format=' %m/%d/%y %H:%M:%S.%f')  # change this if timestamp format every changes in the data
    
    # filter out data outside of time range
    df = df.loc[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
    df.reset_index(drop=True, inplace=True)

    # get list of devices
    devices = df['device_id'].unique()

    df = df.pivot(index='timestamp', columns='device_id', values='value')

    # DF now holds all data that we are concerned with

    #
    # (1) Plot raw barometric data
    #
    df.plot(label=df.columns, figsize=(5, 3))
    plt.xlabel("Time")
    plt.ylabel("Pressure")
    plt.show()

    #
    # (2) Plot the sample rates as a verification of missing samples (not working)
    #
    #diff = df.set_index('columns').diff()
    #df.insert(2, 'diff', diff, True)
    #df.head()

    #
    # (3) Generate Spectrogram
    #

    for device in devices:
        df.interpolate(method='linear', axis=0)  # linear interpolation for any missing samples
        df[device] *= 100  # convert to Pa from hPa

        welchB = 600
        welch0 = 100
        NFFT = 2^next_pow_2(welchB)
        w_window = hamming(welchB)

        f, t, Sxx = spectrogram(df[device], fs=20, window=w_window, noverlap=welch0, nfft=NFFT, return_onesided=True, mode='psd')
        plt.pcolormesh(t, f, np.log10(Sxx), shading='gouraud')
        plt.ylabel('Frequency [Hz]')
        plt.xlabel('Time [sec]')
        plt.colorbar(label='Pa^2/Hz')
        plt.show()
        exit(0)

if __name__ == "__main__":
    main()
