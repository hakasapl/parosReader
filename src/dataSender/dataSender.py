import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import time
from datetime import datetime
import os
import csv
import argparse
import pandas as pd

def main():

    parser = argparse.ArgumentParser(description='Sends the past hour of data to influxdb')
    parser.add_argument("url", help="URL of influxdb remote server", type=str)
    parser.add_argument("org", help="InfluxDB Org", type=str)
    parser.add_argument("token", help="InfluxDB API token", type=str)
    parser.add_argument("bucket", help="InfluxDB Bucket name", type=str)
    parser.add_argument("-l", "--logdir", help="Log directory", action='append', required=True)
    parser.add_argument("-t", "--time", help="Send specific csv")
    parser.add_argument("-c", "--chunk", help="CSV chunk size in # of lines", default=1000)
    args = parser.parse_args()

    # create influxdb objects
    client = influxdb_client.InfluxDBClient(url=args.url, token=args.token, org=args.org)

    # find csv file to send
    if args.time is None:
        # custom time requested to be sent
        cur_time = datetime.utcnow()
        # get the previous hour since this would be called at the new hour by cron
        csv_timestamp = cur_time.replace(hour=cur_time.hour - 1,minute=0,second=0,microsecond=0)
    else:
        cur_time = datetime.fromisoformat(args.time)
        csv_timestamp = cur_time.replace(minute=0,second=0,microsecond=0)

    for logdir in args.logdir:
        log_prefix = os.path.basename(logdir)

        csv_path = os.path.join(
            logdir,
            log_prefix + "_" + datetime.strftime(csv_timestamp, "%Y%m%d"),
            log_prefix + "_" + datetime.strftime(csv_timestamp, "%Y%m%d-%H") + ".txt"
        )

        # read csv in chunks with pandas
        if log_prefix == "BAROLOG":
            csvHeader = ["hostname", "sensor_id", "sys_timestamp", "timestamp", "value"]
        elif log_prefix == "WINDLOG":
            csvHeader = ["hostname", "sensor_id", "timestamp", "adc", "voltage", "value"]
        
        i = 0
        for df in pd.read_csv(csv_path, chunksize=args.chunk, names=csvHeader):
            # convert values
            df["value"] = df["value"].astype(float)

            print("Sending " + log_prefix + " data points [" + str(i * args.chunk) + "-" + str((i + 1) * args.chunk - 1) + "]")
            i += 1
            with client.write_api() as write_api:
                try:
                    write_api.write(
                        record=df,
                        bucket=args.bucket,
                        data_frame_measurement_name="paros1",
                        data_frame_tag_columns=["sensor_id"],
                        data_frame_timestamp_column="timestamp",
                    )
                except InfluxDBError as e:
                    print(e)

if __name__ == "__main__":
    main()