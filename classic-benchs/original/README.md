# Original benchmark sources

These files are byte-identical copies of sources archived by
`cpushowspeed classic collect` under `data/raw/classic/` (see
[`docs/data/classic-benchmark-sources.csv`](../../docs/data/classic-benchmark-sources.csv)).
They are kept unchanged, including CRLF line endings (`.gitattributes` disables
line-ending conversion here). The project's modified, buildable versions are the
sibling directories of `original/`; the [runner design](../../docs/classic-bench.md)
describes what may change.

None of these sources carries a licence or copyright notice. They predate
open-source licensing conventions and have long circulated freely through Netlib,
Usenet and the author's own site; authorship is recorded below.

| File | Source and retrieval | BLAKE3 | Authorship stated in the file |
| --- | --- | --- | --- |
| `dhrystone-2.1/dhry-c` | [netlib `benchmark/dhry-c`](https://www.netlib.org/benchmark/dhry-c), retrieved 2026-09-26 (Last-Modified 1990-08-25). A shell archive of `RATIONALE`, `README_C`, `VARIATIONS`, `dhry.h`, `dhry_1.c`, `dhry_2.c`, `dhry_c.dif` and `submit.frm`; unpack it by parsing, not by executing it. | `2ec5910d1d3f36df235abb8fd0f99ea7d3faea3cf3aac194ce0368cd6bb32b68` | Reinhold P. Weicker (Siemens), C version 2.1 with Rick Richardson, 1988-05-25 |
| `dhrystone-1.1/Dhry1.c` | Member `benchnt/C_Source/Dhry1.c` (1997-03-11) of Roy Longbottom's [`benchnt.zip`](http://www.roylongbottom.org.uk/benchnt.zip), retrieved 2026-09-26; zip BLAKE3 `f661844bfea8c2256241097e338ca049efa8f88221ff7cb2242e7eca3a868b24` | `1bebc5ad1056d59747558e13d67031eb8782d0feb676b88428d6cd3ad978d8be` | Weicker (CACM 27(10), 1984); C translation by Rick Richardson; ANSI C by James Day; PC version by Roy Longbottom, 1996 |
| `whetstone/whets.c` | Roy Longbottom's [`whets.c`](http://www.roylongbottom.org.uk/whets.c), retrieved 2026-09-26 (Last-Modified 2008-09-26) | `f031750c64d3e5e465538ccec3154118b64a5389dadcd102476d24d4d7d65868` | Concept Brian Wichmann (NPL); Harold Curnow (CCTA, 1972); C/C++ version Roy Longbottom, 1996; timers Al Aburto; approved by Harold Curnow |
| `linpack/linpackc.new` | [netlib `benchmark/linpackc.new`](https://www.netlib.org/benchmark/linpackc.new), retrieved 2026-10-03 (Last-Modified 1994-03-12) | `e5c7bc8cc389a18a9127634d501a9f6cfa3a1f7a6964a613275e3e1d5d51a05b` | C translation by Bonnie Toy, 1988; modified by Will Menninger, 1993; daxpy fix by Jack Dongarra, 1994-02-25 |

Dhrystone 1.1 is not Richardson's original file: Longbottom's copy already
changes `Proc3(NextRecord.PtrComp)` to `Proc3(&NextRecord.PtrComp)` and adds DOS
console and timing code. No original 1.1 file is archived.
