#include <stdio.h>
int ReadBattery(void);
int main(void) { printf("battery=%d mV\n", ReadBattery()); return 0; }
