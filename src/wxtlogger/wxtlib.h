#define set_wind_conf        "0WU,I=1,A=1,U=M,D=0,N=W,F=1\r\n" // defines est. settings
#define set_wind_parameters "0WU,R=0100100001001000\r\n" // defines what to est.
#define set_ptu_conf        "0TU,I=1,P=H,T=F\r\n" // defines est. settings
#define set_ptu_parameters    "0TU,R=1101000011010000\r\n" // defines what to est.
#define set_rain_conf        "0RU,U=M,S=M,Z=M\r\n" // defines est. settings
#define set_rain_parameters "0RU,R=1011010010110100\r\n" // defines what to est.
#define set_super_conf        "0SU,S=N,H=Y,I=5\r\n" //update 10s, err msg disabled, heating control enabled
#define set_super_parameters "0SU,R=1111000000100000\r\n" // include voltage in comp
#define reset_rain            "0XZRU\r\n" // reset precipitation counters
#define get_composite        "0R0\r\n" // request certain things from sensors
#define set_comm            "0XU,M=P,C=3,B=4800,L=25\r\n" // 3=RS485, 2=RS232, L=RS485delay(ms)
#define get_comm            "0XU\r\n" // get communication settings

/**
 * Returns the difference between the provided timevals
 * @param timestamp The timeval for the last sample
 * @param currenttime The current timeval
 * @return the difference between timestamp and currenttime
 */
double _time_since_last_sample(struct timeval *timestamp, struct timeval *currenttime) {
  double timeA, timeB;
  timeA = timestamp->tv_sec + (timestamp->tv_usec / 1000000.0);
  timeB = currenttime->tv_sec + (currenttime->tv_usec / 1000000.0);
  return timeA - timeB;
}

/**
 * Prints 1 input string to the provided file
 * @param file The file to print to
 * @param str The tring to print
 */
void print(FILE *file, char str[]) {
  char buffer[1024];
  setbuf(file, buffer);
  printf("%s", str);
  fputs(str, file);
  fflush(file);
}

/**
 * reads the provided file and returns the file size
 * @param fp file to read
 * @return size of input file
 */
int fsize(FILE *fp) {
  int prev = ftell(fp);
  fseek(fp, 0L, SEEK_END);
  int sz = ftell(fp);
  fseek(fp, prev, SEEK_SET); //go back to where we were
  return sz;
}

/**
 * Checks to see if the folder exists. If it doesn't, it creates it.
 * @param dir The directory to check
 */
void check_directory(char dir[]) {
  struct stat st = {0};
  if (stat(dir, &st) == -1) {
    mkdir(dir, 0777);
  }
  char cmd[] = "chmod 777 -R ";
  strcat(cmd, dir);
  system(cmd);
}

int isOSX() {
  #ifdef __APPLE__ 
    return 1; 
  #else 
    return 0; 
  #endif 
}

