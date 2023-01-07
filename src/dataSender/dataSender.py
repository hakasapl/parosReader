import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import time
from datetime import datetime
import os
import csv

def main():

    parser = argparse.ArgumentParser(description='Sends the past hour of data to influxdb')
    parser.add_argument("url", help="URL of influxdb remote server", type=str)
    parser.add_argument("org", help="InfluxDB Org", type=str)
    parser.add_argument("token", help="InfluxDB API token", type=str)
    parser.add_argument("bucket", help="InfluxDB Bucket name", type=str)
    parser.add_argument("-l", "--logdir", help="Log directory", nargs='+', required=True)
    parser.add_argument("-t", "--time", help="Send specific csv")
    args = parser.parse_args()

    # define influxdb params
    bucket = "paros-datastream"
    org = "paros"
    token = "0ezvek442zpRbMEG_4sJ4m-2Ld8Yfwyidpa76OjC5p8HBWqigNWJoiVYQUOitqI0vCvm4VBat4O36UbogZ5RDg=="
    url = "https://influxdb.paros.casa.umass.edu/"
    logdirs = ["/opt/BAROLOG", "/opt/WINDLOG"]

    # create influxdb objects
    client = influxdb_client.InfluxDBClient(url=args.url, token=args.token, org=args.org)
    write_api = client.write_api(write_options=SYNCHRONOUS)

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

        if os.path.exists(csv_path):
            # found log file
            with open(csv_path) as csv_file:
                csvreader = csv.reader(csv_file)

                for row in csvreader:
                    # create influxdb point
                    p_hostname = row[0]
                    p_sensorid = row[1]
                    p_timestamp = row[2]
                    p_sensortimestamp = row[3]
                    p_value = row[4]

                    p = influxdb_client.Point(p_hostname) \
                        .tag("dtype", logfiles_prefix[i]) \
                        .tag("sensor_id", p_sensorid) \
                        .time(p_sensortimestamp) \
                        .field("sys_timestamp", p_timestamp) \
                        .field("value", p_value)

                    write_api.write(bucket=args.bucket, org=args.org, record=p)

        else:
            # didn't find log file
            print("Log file " + csv_path + " doesn't exist!")

if __name__ == "__main__":
    main()