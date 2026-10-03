/*
 * Entry points of the modified classical benchmark sources (CPUShowSpeed).
 *
 * Each *_run call executes the requested number of passes of the original
 * measured code and stores in *Seconds the time that code measured, using
 * the original program's own timing boundaries. The return value is 0 when
 * the program's result check passes and nonzero otherwise. Written in C89 so
 * that the old sources can include it unchanged in their own dialect.
 */
#ifndef CLASSIC_KERNEL_H
#define CLASSIC_KERNEL_H

#ifdef __cplusplus
extern "C" {
#endif

/* Monotonic seconds; replaces each program's platform timer. */
double cb_seconds (void);

/* Dhrystone 2.1: work = runs; init returns 1 if compiled with REG. */
int dhry21_init (void);
int dhry21_run (long runs, double *Seconds);

/* Dhrystone 1.1: work = runs. */
int dhry11_init (void);
int dhry11_run (long runs, double *Seconds);

/* Whetstone (whets.c compiled with and without DP): one pass of xtra runs
   whetstones(xtra, 100); work = 10 * xtra million Whetstone instructions,
   *Seconds is the sum of the section times. */
int whet_sp_run (long xtra, double *Seconds);
int whet_dp_run (long xtra, double *Seconds);

/* LINPACK n = 100, lda = 201 (compiled with and without SP): roll = 1 for
   rolled, 0 for unrolled BLAS; work = 2n^3/3 + 2n^2 flops per pass,
   *Seconds = dgefa + dgesl time. */
int linpack_sp_run (long passes, int roll, double *Seconds);
int linpack_dp_run (long passes, int roll, double *Seconds);

#ifdef __cplusplus
}
#endif

#endif
