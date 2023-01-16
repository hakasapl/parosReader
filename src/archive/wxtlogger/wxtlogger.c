#include <syslog.h>
#include <sys/time.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>
#include <dirent.h>
#include <time.h>
#include <errno.h>
#include <signal.h>
#include <sys/ioctl.h>
#include <math.h>
#include "wxtlib.h"

// Sample Rate in Hz
#define samplerate                      1
// Maximum number of sensors
#define maxsensors                      2

// Weather Stations. Need to update this in main() if modified
#ifndef __APPLE__ 
#define wxtdrvr1                        "/dev/ttyUSB2"
#define wxtdrvr2                        "/dev/ttyUSB3"
#else
#define wxtdrvr1                        "/dev/tty.usbserial-00004114"
#define wxtdrvr2                        "/dev/tty.usbserial-00004214"
#endif

// Delay on Serial Port
#define tdelay                          100000

// Max File Size
#define max_output_filesize             10485760 // 10MB = 1024 * 1024 * 10
// Max String Length
#define max_str_len                     1024

/// Struct for storing the weather station data
int debug = 0;

struct wxtdata_t {
  char model[255];
  char version[255];
  char wind_units[255];
  char pressure_units[255];
  char temp_units[255];
  char rain_units[255];
  char rain_rate_units[255];
  double wind_avg;
  int wind_dir;
  double temp;
  double humidity;
  double pressure;
  double rain_accum;
  double rain_rate;
  double hail_accum;
  double hail_rate;
  double voltage;
};

/**
 * Parses input string and stores it in provided buffer
 * @param msg the string to parse
 * @param prefix delimiter before target
 * @param suffix delimiter after target
 * @param tempbuff storage for target
 */
void data_parser(char msg[], char prefix[], char suffix[], char tempbuff[]) {
  int length;
  char *response_parser;
  if (strstr(msg, prefix) != NULL) {
    response_parser = strstr(msg, prefix); // chop off portion of msg prior to target data
    length = strcspn((response_parser + strlen(prefix)), suffix); // get length of target data
    strncpy(tempbuff, (response_parser + strlen(prefix)), length);
    tempbuff[length] = '\0';
  } else {
    sprintf(tempbuff, "NaN");
  }
}

/**
 * Reads contents of specified file descriptor
 * @param fd_ser weather station file descriptor
 * @param wxt_response buffer to store the read data
 * @return 0 on success, -1 on failure
 */
int wxtread(int fd_ser, char *wxt_response) {
  wxt_response[0] = '\0';
  int msglen;
  msglen = 0;
  ioctl(fd_ser, FIONREAD, &msglen);
  if (msglen > 0) {
    msglen = read(fd_ser, wxt_response, msglen);
    wxt_response[msglen] = '\0';
  }
  tcflush(fd_ser, TCIOFLUSH);
  if (debug) {
    printf("wxtread returns %s\n", wxt_response);
  }
  return msglen > 0 ? msglen : -1;
}

/**
 * Sends a command to the specified file descriptor
 * @param fd_ser weather station file descriptor
 * @param data_out command to write
 * @return 0 on success, -1 on failure
 */
int wxtwrite(int fd_ser, char *data_out) {
  int out_bytes;
  tcflush(fd_ser, TCIOFLUSH);
  usleep(tdelay);
  out_bytes = write(fd_ser, data_out, strlen(data_out));
  if (out_bytes < 0) {
    fputs("write() failed!\n", stderr);
    return -1;
  }
  if (debug) {
    printf("wxtwrite %s\n", data_out);
  }
  return 0;
}

/**
 * Sends set_comm to specified file descriptor
 * @param fd_ser weather station file descriptor
 * @return 0 on success, -1 on failure
 */
int wxt_comms_configure(struct wxtdata_t *wxtdata, int fd_ser) {
  char wxt_response[max_str_len];
  char* wxt_rptr = wxt_response;

  // set the comm protocol
  wxtwrite(fd_ser, set_comm);
  usleep(tdelay);
  (void) wxtread(fd_ser, wxt_rptr);

  // get the comm settings
  wxtwrite(fd_ser, get_comm);
  usleep(tdelay);
  int result = wxtread(fd_ser, wxt_rptr);
  char temp[255];

  // loop for a while until we read what we want
  int cnt = 10;
  do {
    printf("Reading comm config: %s\n", wxt_response);
    if (strstr(wxt_response, "V=") != NULL) {
      data_parser(wxt_response, "V=", "\r", temp);
      strcpy(wxtdata->version, temp);
    }
    if (strstr(wxt_response, "N=") != NULL) {
      data_parser(wxt_response, "N=", ",", temp);
      strcpy(wxtdata->model, temp);
      break;
    }
    // if we didn't see model wait a bit and read again
    usleep(tdelay);
    wxtread(fd_ser, wxt_rptr);
  } while (--cnt > 0);
  
  return result;
}

/**
 * Sends set_wind_conf and set_wind_parameters to specified file descriptor and parses response into given wxtdata_t
 * @param wxtdata wxtdata_t struct for the weather station
 * @param fd_ser weather station file descriptor
 * @return 0 on success, -1 on failure
 */
int wxt_wind_configure(struct wxtdata_t *wxtdata, int fd_ser) {
  // define variable
  char switch_str[255];
  char wxt_response[max_str_len];
  char* wxt_rptr = wxt_response;

  // send request
  wxtwrite(fd_ser, set_wind_conf);
  usleep(tdelay);
  (void) wxtread(fd_ser, wxt_rptr);

  // wind units
  if (strstr(wxt_response, "U=") != NULL) {
    data_parser(wxt_response, "U=", ",", switch_str);
    switch (switch_str[0]) {
      case 'M':
        strcpy(wxtdata->wind_units, "m/s");
        break;
      case 'K':
        strcpy(wxtdata->wind_units, "km/h");
        break;
      case 'S':
        strcpy(wxtdata->wind_units, "mph");
        break;
      case 'N':
        strcpy(wxtdata->wind_units, "knots");
        break;
      default:
        strcpy(wxtdata->wind_units, "ERROR - invalid wind units response");
        break;
    }
  }

  // set wind parameters
  wxtwrite(fd_ser, set_wind_parameters);
  usleep(tdelay);
  return wxtread(fd_ser, wxt_rptr);
}

/**
 * Sends set_wind_conf and set_wind_parameters to specified file descriptor and parses response into given wxtdata_t
 * @param wxtdata wxtdata_t struct for the weather station
 * @param fd_ser weather station file descriptor
 * @return 0 on success, -1 on failure
 */
int wxt_rain_configure(struct wxtdata_t *wxtdata, int fd_ser) {
  // define variable
  char switch_str[255];
  char wxt_response[max_str_len];
  char* wxt_rptr = wxt_response;

  // send request
  wxtwrite(fd_ser, set_rain_conf);
  usleep(tdelay);
  (void) wxtread(fd_ser, wxt_rptr);

  // wind units
  if (strstr(wxt_response, "U=") != NULL) {
    data_parser(wxt_response, "U=", ",", switch_str);
    switch (switch_str[0]) {
      case 'M':
        strcpy(wxtdata->rain_units, "mm");
        strcpy(wxtdata->rain_rate_units, "mm/h");
        break;
      case 'I':
        strcpy(wxtdata->rain_units, "in");
        strcpy(wxtdata->rain_rate_units, "in/h");
        break;
      default:
        strcpy(wxtdata->rain_units, "ERROR - invalid rain units response");
        strcpy(wxtdata->rain_rate_units, "ERROR - invalid rain rate units response");
        break;
    }
  }

  // set wind parameters
  wxtwrite(fd_ser, set_rain_parameters);
  usleep(tdelay);
  return wxtread(fd_ser, wxt_rptr);
}

/**
 * Sends set_ptu_conf and set_ptu_parameters to specified file descriptor and parses response into given wxtdata_t
 * @param wxtdata wxtdata_t struct for the weather station
 * @param fd_ser weather station file descriptor
 * @return 0 on success, -1 on failure
 */
int wxt_ptu_configure(struct wxtdata_t *wxtdata, int fd_ser) {
  // define variable
  char switch_str[255];
  char wxt_response[max_str_len];
  char* wxt_rptr = wxt_response;

  // send ptu_cmd
  wxtwrite(fd_ser, set_ptu_conf);
  usleep(tdelay);
  (void) wxtread(fd_ser, wxt_rptr);

  // pressure units ('P')
  if (strstr(wxt_response, "P=") != NULL) {
    data_parser(wxt_response, "P=", ",", switch_str); // pressure units
    switch (switch_str[0]) {
      case 'H':
        strcpy(wxtdata->pressure_units, "hPa");
        break;
      case 'P':
        strcpy(wxtdata->pressure_units, "Pa");
        break;
      case 'B':
        strcpy(wxtdata->pressure_units, "bar");
        break;
      case 'M':
        strcpy(wxtdata->pressure_units, "mmHg");
        break;
      case 'I':
        strcpy(wxtdata->pressure_units, "inHg");
        break;
      default:
        strcpy(wxtdata->pressure_units, "ERROR - invalid pressure units response");
        break;
    }
  }

  // pressure units ('T')
  switch_str[0] = '\0';
  if (strstr(wxt_response, "T=") != NULL) {
    data_parser(wxt_response, "T=", ",", switch_str); // temp units
    switch (switch_str[0]) {
      case 'C':
        strcpy(wxtdata->temp_units, "C");
        break;
      case 'F':
        strcpy(wxtdata->temp_units, "F");
        break;
      default:
        strcpy(wxtdata->temp_units, "ERROR - invalid temperature units response");
        break;
    }
  }

  wxtwrite(fd_ser, set_ptu_parameters);
  usleep(tdelay);
  return wxtread(fd_ser, wxt_rptr);
}

/**
 * Sends set_super_conf and set_super_parameters to specified file descriptor and parses response into given wxtdata_t
 * @param wxtdata wxtdata_t struct for the weather station
 * @param fd_ser weather station file descriptor
 * @return 0 on success, -1 on failure
 */
int wxt_supervisor_configure(struct wxtdata_t *wxtdata, int fd_ser) {
  // define variable
  char wxt_response[max_str_len];
  char* wxt_rptr = wxt_response;

  // send ptu_cmd
  wxtwrite(fd_ser, set_super_conf);
  usleep(tdelay);
  (void) wxtread(fd_ser, wxt_rptr);

  wxtwrite(fd_ser, set_super_parameters);
  usleep(tdelay);
  return wxtread(fd_ser, wxt_rptr);
}

/**
 * Configures the serial port at the give file descriptor
 * @param fd file descriptor for the barometer
 * @return 0 on success, -1 on failure
 */
int configure_serial(int fd_ser) {
  struct termios options;

  // get the current serial port attributes
  if (tcgetattr(fd_ser, &options) != 0) {
    close(fd_ser);
    return -1;
  }

  // set the baud rate (use 4800 normally, 19200 for service cable)
  (void) cfsetispeed(&options, B4800);
  (void) cfsetospeed(&options, B4800);

  // set the data format to 8 bits, no parity, one stop (8N1)
  options.c_cflag &= ~(CSIZE | PARENB | CSTOPB);
  options.c_cflag |= CS8;

  // enable the receiver and set local mode
  options.c_cflag |= (CLOCAL | CREAD);

  // disable echo - needed when using USB-RS485 cable
  options.c_lflag &= ~(ECHO | ECHOE);

  // set the new comm port attributes
  tcsetattr(fd_ser, TCSANOW, &options);

  // delay to give time for the change to settle
  (void) tcflush(fd_ser, TCIOFLUSH);
  (void) usleep(tdelay);
  (void) tcflush(fd_ser, TCIOFLUSH);

  // return success
  return 0;
}

/**
 * Generates a filename and stores it in given char[] using the time and device number
 * @param filename storage for generated filename
 * @param nowtime time to use for making the filename
 * @param dev device number
 */
void make_filename(char filename[], time_t time, int dev) {
  char dir[max_str_len];
  char file[max_str_len];
  filename[0] = '\0';
  struct tm *filetime = localtime(&time);
  strftime(dir, max_str_len, "data-%Y%m%d", filetime);
  check_directory(dir);
  strftime(file, max_str_len, "%Y%m%d-%H%M%S.txt", filetime);
  sprintf(filename, "./%s/WX%d-%s", dir, dev, file);
}

/**
 * Generates the header string that is used at the beginning of each file
 * @param outbuff output buffer for the generated string
 * @param wind_units wind units
 * @param pressure_units pressure units
 * @param temp_units temperature units
 */
void make_header_string(char outbuff[], char model[], char version[], char wind_units[], char pressure_units[], char temp_units[],
        char rain_units[], char rain_rate_units[]) {
  int nbytes = 0;
  nbytes = sprintf(outbuff, "Model Number: %s (Version %s)\n", model, version);
  nbytes += sprintf(outbuff + nbytes, "Sample rate: %d (Hz)\n", samplerate);
  nbytes += sprintf(outbuff + nbytes, "Wind speed units: %s\n", wind_units);
  nbytes += sprintf(outbuff + nbytes, "Pressure units: %s\n", pressure_units);
  nbytes += sprintf(outbuff + nbytes, "Temperature units: %s\n", temp_units);
  nbytes += sprintf(outbuff + nbytes, "Rain Accum units: %s\n", rain_units);
  nbytes += sprintf(outbuff + nbytes, "Rain Rate units: %s\n\n", rain_rate_units);
  nbytes += sprintf(outbuff + nbytes, "Index, Hour, Minute, Second, Direction, Speed, Temp, Humidity, Pressure, Rain Accum, Rain Rate, Hail Accum, Hail Rate, Voltage\n");
  nbytes += sprintf(outbuff + nbytes, "_______________________________________________________________________\n\n");
}

int main(int argc, char *argv[]) {
  
  printf("Starting wxtlogger...\n");
  
  if (argc > 1) {
    debug = 1;
    printf("Debug output enabled\n");
  }

  int fd[maxsensors];
  char fdloc[maxsensors][max_str_len];
  struct wxtdata_t storage[maxsensors];

  int actualNumSensors; // will be set below
  /// Add each of the Weather Stations here
  strcpy(fdloc[0], wxtdrvr1);
  if (actualNumSensors > 1) {
    strcpy(fdloc[1], wxtdrvr2);
  }

 
  int i;
  char wxt_response[max_str_len];
  char* wxt_rptr = wxt_response;

  // Configure the Weather Stations for sampling
  for (i = 0; i < maxsensors; i++) {
    if ((fd[i] = open(fdloc[i], O_RDWR | O_NOCTTY | O_NONBLOCK)) < 0) {
      printf("Can't open file descriptor at %s\n", fdloc[i]);
      exit(0);
    } else {
      printf("Opened file descriptors at %s : %d\n", fdloc[i], fd[i]);
    }

    if (configure_serial(fd[i]) < 0) {
      printf("Can't configure serial at %s\n", fdloc[i]);
      exit(0);
    } else {
      printf("Successfully configured serial at %s\n", fdloc[i]);
    }

    if (wxt_comms_configure(&storage[i], fd[i]) < 0) {
      printf("Can't configure comms at %s\n", fdloc[i]);
      //exit(0);
      // see actualNumSensors = i + 1 below
      printf("Actual number of sensors is %d\n", i);
    } else {
      printf("Successfully configured Weather Station comms at %s\n", fdloc[i]);
      // here we're assuming that we've got sensors plugged in from lowest port to highest so
      // once we hit one that we can't configure that determines our actual number of sensors
      actualNumSensors = i + 1;
    }
  }
  
 
  
  struct wxtdata_t wxtdata1 = {"WXT-???", "?.?", "m/s", "hPa", "F", "mm", "mm/h", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
  storage[0] = wxtdata1;
  if (actualNumSensors > 1) {
    struct wxtdata_t wxtdata2 = {"WXT-???", "?.?", "m/s", "hPa", "F", "mm", "mm/h", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    storage[1] = wxtdata2;
  }

  for (i = 0; i < actualNumSensors; i++) {
    printf("Configuring Weather Station at %s\n", fdloc[i]);
    wxt_wind_configure(&storage[i], fd[i]);
    usleep(tdelay);
    wxt_ptu_configure(&storage[i], fd[i]);
    usleep(tdelay);
    wxt_rain_configure(&storage[i], fd[i]);
    usleep(tdelay);
    wxt_supervisor_configure(&storage[i], fd[i]);
    usleep(tdelay);

    printf("Successfully configured Weather Station at %s\n", fdloc[i]);

    // Throw away couple data samples
    wxtwrite(fd[i], get_composite);
    usleep(tdelay);
    (void) wxtread(fd[i], wxt_rptr);
    
    wxtwrite(fd[i], get_composite);
    usleep(tdelay);
    (void) wxtread(fd[i], wxt_rptr);

    wxtwrite(fd[i], get_composite);
    usleep(tdelay);
  }

  // Time and Output
  int sampleindex = 0;
  struct timeval wxt_timestamp, currenttime;
  gettimeofday(&wxt_timestamp, NULL);
  gettimeofday(&currenttime, NULL);
  time_t nowtime = currenttime.tv_sec;
  struct tm *nowtm = localtime(&nowtime);
  double time_since_last_sample;

  char tempbuff[255];
  char timestr[255];
  char outbuff[255];
  int nbytes;
  int day = nowtm->tm_yday;

  // File Management - open a log file for each weather station
  FILE * outfile[maxsensors];
  char filename[255];
  for (i = 0; i < actualNumSensors; i++) {
    make_filename(filename, nowtime, i + 1);
    outfile[i] = fopen(filename, "w");
    make_header_string(outbuff, storage[i].model, storage[i].version,
            storage[i].wind_units, storage[i].pressure_units, storage[i].temp_units,
            storage[i].rain_units, storage[i].rain_rate_units);
    print(outfile[i], outbuff);
  }

  // To prevent busy-waiting
  fd_set active_fd_set, read_fd_set;
  FD_ZERO(&active_fd_set);
  for (i = 0; i < actualNumSensors; i++) {
    FD_SET(fd[i], &active_fd_set);
  }
  struct timeval timeout;
  timeout.tv_sec = 0;
  timeout.tv_usec = 0;
  double sec, usec;

  for (;;) {

    // get the time since the last data sample
    gettimeofday(&currenttime, NULL);
    nowtime = currenttime.tv_sec;
    nowtm = localtime(&nowtime);
    time_since_last_sample = _time_since_last_sample(&currenttime, &wxt_timestamp);

    // determine timeout to timeout at next sample time
    if (samplerate - time_since_last_sample <= 0) {
      timeout.tv_sec = 0;
      timeout.tv_usec = 0;
    } else {
      usec = modf(samplerate - time_since_last_sample, &sec);
      timeout.tv_sec = (int) sec;
      timeout.tv_usec = (int) (usec * 1000000);
    }

    // call select to wait for timeout to expire
    read_fd_set = active_fd_set;
    select(FD_SETSIZE, &read_fd_set, NULL, NULL, &timeout);

    // if new day, open a new file
    if (day != nowtm->tm_yday) {
      for (i = 0; i < actualNumSensors; i++) {

        // close current log file
        fclose(outfile[i]);

        // open a new log file
        make_filename(filename, nowtime, i + 1);
        if ((outfile[i] = fopen(filename, "w")) == NULL) {
          printf("Unable to open log file for sensor %d\n", i);
          exit(0);
        }
        make_header_string(outbuff, storage[i].model, storage[i].version,
                storage[i].wind_units, storage[i].pressure_units, storage[i].temp_units,
                storage[i].rain_units, storage[i].rain_rate_units);
        print(outfile[i], outbuff);
      }
      day = nowtm->tm_yday;
    }

    // if sample time, get sample from each weather station
    if (time_since_last_sample >= samplerate) {

      //tempbuff[0] = '\0';
      //outbuff[0] = '\0';

      // get the time stamp for the current data sample
      wxt_timestamp = currenttime;
      nbytes = strftime(timestr, 255, "%H, %M, %S", nowtm);
      sprintf(timestr + nbytes,
#ifndef __APPLE__ 
              ".%06ld",
#else 
              ".%06d",
#endif
              wxt_timestamp.tv_usec);

      for (i = 0; i < actualNumSensors; i++) {

        // get response from previous request
        (void) wxtread(fd[i], wxt_rptr);

        // request next response
        wxtwrite(fd[i], get_composite);

        // clear the data buffers
        tempbuff[0] = '\0';
        outbuff[0] = '\0';

        // clear old data values
        storage[i].wind_avg = 0;
        storage[i].wind_dir = 0;
        storage[i].temp = 0;
        storage[i].humidity = 0;
        storage[i].pressure = 0;

        storage[i].rain_accum = 0;
        storage[i].rain_rate = 0;
        storage[i].hail_accum = 0;
        storage[i].hail_rate = 0;

        storage[i].voltage = 0;

        // parse the composite data response
        data_parser(wxt_response, "Sm=", "M", tempbuff);
        storage[i].wind_avg = atof(tempbuff);
        data_parser(wxt_response, "Dm=", "D", tempbuff);
        storage[i].wind_dir = atoi(tempbuff);
        data_parser(wxt_response, "Ta=", "F", tempbuff);
        storage[i].temp = atof(tempbuff);
        data_parser(wxt_response, "Ua=", "P", tempbuff);
        storage[i].humidity = atof(tempbuff);
        data_parser(wxt_response, "Pa=", "H", tempbuff);
        storage[i].pressure = atof(tempbuff);

        data_parser(wxt_response, "Rc=", "M", tempbuff);
        storage[i].rain_accum = atof(tempbuff);
        data_parser(wxt_response, "Ri=", "M", tempbuff);
        storage[i].rain_rate = atof(tempbuff);
        data_parser(wxt_response, "Hc=", "M", tempbuff);
        storage[i].hail_accum = atof(tempbuff);
        data_parser(wxt_response, "Hi=", "M", tempbuff);
        storage[i].hail_rate = atof(tempbuff);

        data_parser(wxt_response, "Vs=", "V", tempbuff);
        storage[i].voltage = atof(tempbuff);

        // write the composite data to the appropriate log file
        sprintf(outbuff, "%d, %s, %d, %.1lf, %.1lf, %.1lf, %.1lf, %.1lf, %.1lf, %.1lf, %.1lf, %.1lf\n",
                sampleindex,
                timestr,
                storage[i].wind_dir,
                storage[i].wind_avg,
                storage[i].temp,
                storage[i].humidity,
                storage[i].pressure,

                storage[i].rain_accum,
                storage[i].rain_rate,
                storage[i].hail_accum,
                storage[i].hail_rate,

                storage[i].voltage);
        print(outfile[i], outbuff);

        // split file if exceeds given maximum file size
        if (fsize(outfile[i]) > max_output_filesize) {

          // close current log file
          fclose(outfile[i]);

          // open a new log file
          make_filename(filename, nowtime, i + 1);
          if ((outfile[i] = fopen(filename, "w")) == NULL) {
            printf("Unable to open log file for sensor %d\n", i);
            exit(0);
          }
          make_header_string(outbuff, storage[i].model, storage[i].version,
                  storage[i].wind_units, storage[i].pressure_units, storage[i].temp_units,
                  storage[i].rain_units, storage[i].rain_rate_units);
          print(outfile[i], outbuff);
        }

      } // end for each sensor


      sampleindex++;

    }
  }
}
