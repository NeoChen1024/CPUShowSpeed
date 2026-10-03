/* Monotonic clock shared by the modified benchmark sources (CPUShowSpeed). */
#define _POSIX_C_SOURCE 199309L

#include <time.h>

#include "classic_kernel.h"

double cb_seconds(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}
