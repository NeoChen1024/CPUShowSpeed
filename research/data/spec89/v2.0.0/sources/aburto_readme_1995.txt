X-Google-Language: ENGLISH,ASCII-7-bit
X-Google-Thread: 10cbb9,1e2924f2ef715cc0
X-Google-Attributes: gid10cbb9,public
X-Google-Thread: f57db,e201a8b16d9f11ae
X-Google-Attributes: gidf57db,public
X-Google-Thread: 110292,1e2924f2ef715cc0
X-Google-Attributes: gid110292,public
X-Google-Thread: f8403,1e2924f2ef715cc0
X-Google-Attributes: gidf8403,public
From: aburto@nosc.mil (Alfred A. Aburto)
Subject: Re: Debate: PowerMac "trounces" Pentium - info
Date: 1995/07/26
Message-ID: <1995Jul26.140044.7939@nosc.mil>
X-Deja-AN: 106858130
sender: news@nosc.mil
references: <3un17t$fva@news.service.uci.edu> <3uuep2$cre@newsbf02.news.aol.com> <3uuo75$qcm@news.service.uci.edu>
organization: NCCOSC RDT&E Division, San Diego, CA
newsgroups: comp.sys.powerpc,comp.sys.mac.advocacy,comp.sys.intel,comp.benchmarks

Hello,

I'd just mention that I have 'benchmark' C programs and results 
some of which are trivial and some not so trivial (such as 'sim'
and 'fhourstones (C4)'

Attached below is a README file ...    

Al Aburto
aburto@marlin.nosc.mil

##########################################################################
LATEST RESULTS AS OF 06 Mar 1995:
                     08 Mar 1995: added clinpack results...
##########################################################################
This directory contains a collection of the source code and the results
of a number of public benchmarks (in 'c').  It is maintained by Al Aburto
of the Naval Command, Control and Ocean Surveillance Center (NCCOSC)
RDT&E Division (NRaD) in San Diego, CA.  If you have contributions
(program results or programs) or any comments please send them to 
aburto@marlin.nosc.mil.

All 'c' programs and tables of results ('.tbl') are available via
anonymous ftp to 'ftp.nosc.mil' in directory 'pub/aburto'. The IP
address for ftp.nosc.mil is: 128.49.192.51

PLEASE NOTE: The file 'bench.tar.gz' is a gzip compressed tar file of
all programs and results. This is the only BINARY file. All other files
are ASCII. To get bench.tar.gz be sure to set ftp to BINARY mode.

A brief description of the test programs available follows:

 (1) sim
     An integer program that compares DNA segments for  
     similarity.
		 
     Source: sim.shar
     Result: sim.tbl

	
 (2) fhourstones
     An integer program to find solutions to the 'connect-4' game.

     Source: c4.shar
     Result: c4.tbl


 (3) dhrystone
     A synthetic integer program which provides a MIPS rating
     based upon a 'typical' instruction mix. Very sensitive to 
     optimization and results will appear erratic unless degree
     of optimization is carefully tracked.

     Source: dhry.shar
     Result: dhry.tbl

	
 (4) nsieve
     An integer program which generates prime numbers based on
     the Sieve of Eratosthenes using array sizes from 8 KBytes to
     2 MBytes. A nsieve MIPS rating is provided but the nsieve
     instruction mix is NOT 'typical'.
		 
     Nsieve can reveal the 'knees' in performance relative to
     memory and cache size as illustrated below (item 16).

     Source: nsieve.c
     Result: nsieve.tbl

	
 (5) heapsort
     An integer program which uses the 'heap sort' method of
     sorting a random array of long integers up to 2 MBytes in
     size. A heapsort MIPS rating is provided but it is NOT 
     representative of a 'typical' instruction mix.

     Source: heapsort.c
     Result: heapsort.tbl

	
 (6) hanoi
     An integer program which solves the Towers of Hanoi puzzle
     using recursive function calls. 

     Source: hanoi.c
     Result: hanoi.tbl

	
 (7) queens
     An integer program that solves the "14 Queens Problem". That is,
     the program finds all ways to place 14 queens on a 14 X 14
     square "chess" board such that no queen can capture another.

     Source: queens.c
     Result: queens.tbl


 (8) flops
     Estimates MFLOPS rating for specific FADD, FSUB, FMUL, and
     FDIV instruction mixes. Four distinct MFLOPS ratings are
     provided based on the FDIV weightings from 25% to 0% and
     using register-register operations. Works with both scalar
     and vector machines. Since the program trys to maximize
     register usage the results are NOT sensitive to main memory
     speed. In this sense flops yields a peak rating.

     Source: flops20.c
     Result: flops_1.tbl, flops_2.tbl, flops_3.tbl, flops_4.tbl

	
 (9) clinpack
     This is the Linpack program (floating-point) converted to c.
     Results here are sensitive to cache effects and memory speed.

     Source: clinpack.c
     Result: clinpack.dpr, clinpack.dpu, clinpack.spr, clinpack.spu


(10) fft
     An FFT test program from Ron Mayer (mayer@acuson.com). Program
     times a 131072 point FFT.

     Source: fft.shar
     Result: fft.tbl


(11) tfftdp
     This program performs FFT's using the Duhamel-Hollman
     method for FFT's from 32 to 262,144 points in size.

     Source: tfftdp.c
     Result: tfftdp.tbl


(12) matrix multiply (mm)
     This program (mm.c) contains 9 different algorithms for 
     doing matrix multiplication (500 X 500 standard size). 
     Results illustrate the enormous effects of cache thrashing
     versus algorithm, machine, compiler, and compiler options.

     Source: mm.c
     Result: mm_1.tbl, mm_2.tbl

		 
(13) SPEC results
     SPEC results from vendor Performance Briefs and results
     collected off the network are also available.

     Result: specin89.tbl, specfp89.tbl, specin92.tbl, specfp92.tbl
     speccorr.tbl


(14) Timer programs
     Timer routines in 'c' are also available.

     Source: timers_a.c, timers_b.c


(15) FAQ's
     Some helpful FAQ files are also available:

     FAQ: spec.faq, nistlib.faq, bench.faq


(16) Nsieve example results:

   -----------------------------------------------------------------------
   Sieve of Eratosthenes (Scaled to 10 Iterations)
   Version 1.2b, 26 Sep 1992
	
   R4400 100 MHz, 16 KByte I/D internal caches, 1 MByte external cache
   cc -DUNIX -mips2 -sopt-so=4 -O3 -non_shared nsieve.c -o nsieve

   Array Size   Number   Last Prime     Linear    RunTime    MIPS  caches
   (Bytes)    of Primes               Time(sec)    (Sec)
      8191       1899        16381      0.022      0.022    76.2
     10000       2261        19997      0.027      0.026    76.8___ 16KB
     20000       4202        39989      0.053      0.060    69.0
     40000       7836        79999      0.106      0.152    55.0
     80000      14683       160001      0.213      0.326    51.7
    160000      27607       319993      0.425      0.680    50.2
    320000      52073       639997      0.850      1.432    48.1
    640000      98609      1279997      1.700      3.451    40.3___ 1 MB
   1280000     187133      2559989      3.401     11.772    23.9
   2560000     356243      5119997      6.801     44.810    12.6

   -----------------------------------------------------------------------
   R4000PC 100 MHz CPU, 8 KByte I/D internal caches, NO external cache
   cc -DUNIX -mips2 -sopt-so=4 -O3 -non_shared nsieve.c -o nsieve

   Array Size   Number   Last Prime     Linear    RunTime    MIPS
    (Bytes)   of Primes               Time(sec)    (Sec)
      8191       1899        16381      0.023      0.023    72.1___ 8 KB
     10000       2261        19997      0.028      0.047    43.6
     20000       4202        39989      0.056      0.184    22.4
     40000       7836        79999      0.112      0.435    19.1
     80000      14683       160001      0.225      0.944    17.9
    160000      27607       319993      0.449      1.984    17.2
    320000      52073       639997      0.899      4.133    16.7
    640000      98609      1279997      1.797      8.733    15.9
   1280000     187133      2559989      3.594     18.228    15.4
   2560000     356243      5119997      7.188     38.085    14.9

Al Aburto
aburto@marlin.nosc.mil





