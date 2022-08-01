import argparse
import enum
import os
import datetime
from time import strftime
import pandas as pd

def main():
    now = datetime.datetime.now()

    parser = argparse.ArgumentParser()
    parser.add_argument("data", help="Location of data output", type=str, default="data")
    parser.add_argument("-s", "--start-time", help="Location of output data", type=str, default="1970-01-01-00-00-00")
    parser.add_argument("-e", "--end-time", help="Period, in ms, between each data push", type=str, default=now.strftime("%Y-%m-%d-%H-%M-%S"))
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
    print(df.head())
    
    # filter out data outside of time range
    df = df.loc[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
    df.reset_index(drop=True, inplace=True)


if __name__ == "__main__":
    main()