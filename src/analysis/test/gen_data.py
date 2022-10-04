import argparse
import time
import os
import random
import datetime

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "dataset", nargs=1, help="Name of text file dataset to use in the 'datasets' folder")
    parser.add_argument("-o", "--output", help="Location of output data")
    parser.add_argument("-p", "--period", help="Period, in ms, between each data push", type=int, default=50)
    parser.add_argument("-n", "--numsensors", help="Number of sensors to simulate data for", type=int, default=1)
    args = parser.parse_args()

    DATASET_FILE_PATH = "datasets/" + args.dataset[0] + ".csv"

    if args.output is None:
        OUTPUT_FILE_PATH = "output/" + time.strftime("%Y%m%d-%H%M%S") + ".txt"
    else:
        OUTPUT_FILE_PATH = args.output

    DATA_PERIOD = float(args.period) / 1000

    # check if output file exists, if so delete it
    if os.path.exists(OUTPUT_FILE_PATH):
        os.remove(OUTPUT_FILE_PATH)

    # generate device IDs
    devices = random.sample(range(100000,999999), args.numsensors)

    with open(DATASET_FILE_PATH) as input_data:
        line = input_data.readline()
        while line:
            output_data = open(OUTPUT_FILE_PATH, 'a')
            line = input_data.readline()
            datapoint = line.split(",")

            now = datetime.datetime.now()
            timestamp = " " + now.strftime('%m/%d/%Y %H:%M:%S') + "." + ('%02d' % (now.microsecond / 10000))

            for i,device in enumerate(devices):
                print(device)
                output_list = [str(device), str(timestamp), str(datapoint[i])]
                output_data.write(",".join(output_list) + "\n")

            print("Writing data: " + line, end='')
            output_data.close()
            time.sleep(DATA_PERIOD)


if __name__ == '__main__':
    main()
