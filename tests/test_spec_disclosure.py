import unittest

from cpushowspeed.spec_disclosure import parse_disclosure


class DisclosureTests(unittest.TestCase):
    def test_rate_copies_and_selected_iterations(self):
        csv = b"""valid,1
"Full Results Table"
Benchmark,Base # Copies,Base Selected,Peak # Copies,Peak Selected
500.perlbench_r,32,0,64,0
500.perlbench_r,48,1,96,1
"Selected Results Table"
Benchmark,Base # Copies,Base Selected,Peak # Copies,Peak Selected
500.perlbench_r,48,1,96,1
"CPU(s) enabled","24 cores, 2 chips, 2 threads/core"
"""
        r = parse_disclosure(csv, ".csv", "cpu2017", "rate")
        self.assertEqual(r["hardware"], dict(enabled_cores=24, enabled_chips=2, threads_per_core=2))
        self.assertEqual(len(r["execution"]), 2)
        self.assertEqual(r["modes"]["base"]["minimum"], 48)
        self.assertEqual(r["modes"]["peak"]["maximum"], 96)

    def test_speed_threads_are_not_hardware_threads(self):
        csv = b"""Benchmark,Base # Threads,Base Selected,Peak # Threads,Peak Selected
600.perlbench_s,384,1,1,1
602.gcc_s,384,1,384,1
"CPU(s) enabled","192 cores, 2 chips, 2 threads/core"
"""
        r = parse_disclosure(csv, ".csv", "cpu2026", "speed")
        self.assertEqual(r["hardware"]["threads_per_core"], 2)
        self.assertEqual(r["modes"]["peak"]["minimum"], 1)
        self.assertEqual(r["modes"]["peak"]["maximum"], 384)
        self.assertTrue(all(r["quantity"] == "threads" for r in r["execution"]))

    def test_old_omitted_html_tags_and_peak_unlabelled(self):
        html = b"""<TABLE><TR><TH>Benchmark # and Name<TH>Base # Copies<TH>Base Run Time<TH>Base Ratio<TH>Peak # Copies<TH>Peak Run Time<TH>Peak Ratio
<TR><TD>099.go<TD>1<TD>125<TD>332<TD>3<TD>124<TD>333</TABLE>"""
        r = parse_disclosure(html, ".html", "cpu95", "rate")
        self.assertEqual(r["modes"]["base"]["maximum"], 1)
        self.assertEqual(r["modes"]["peak"]["maximum"], 3)
        html = b"""<TR><TD></TD><TH>Benchmark</TH><TH>Base<BR>Copies</TH><TH>Base Runtime</TH><TH>Base Ratio</TH><TH>Copies</TH></TR>
<TR><TD></TD><TD>164.gzip</TD><TD>2</TD><TD>722</TD><TD>4.50</TD><TD>4</TD></TR>"""
        r = parse_disclosure(html, ".html", "cpu2000", "rate")
        self.assertEqual(r["modes"]["peak"]["minimum"], 4)

    def test_partial_enablement_and_legacy_counts_not_inferred(self):
        for enabled, expected in [
            ("1 core, 1 chip, 2 cores/chip", dict(enabled_cores=1, enabled_chips=1, cores_per_chip=2)),
            ("4", dict(legacy_enabled_cpus=4)),
        ]:
            r = parse_disclosure(('CPU(s) enabled,"' + enabled + '"').encode(), ".csv", "cpu2006", "speed")
            self.assertEqual(r["hardware"], expected)
            self.assertFalse(r["execution"])
            self.assertIsNone(r["modes"]["base"]["minimum"])

    def test_noninteger_thread_disclosure_is_preserved_not_guessed(self):
        body = b'"Selected Results Table"\nBenchmark,Base # Threads,Peak # Threads\n600.perlbench_s,64i,88i\n'
        r = parse_disclosure(body, ".csv", "cpu2017", "speed")
        self.assertEqual(r["modes"]["base"]["status"], "unparsed_reported_value")
        self.assertEqual(r["modes"]["base"]["unparsed_values"], ["64i"])
        self.assertIsNone(r["modes"]["base"]["minimum"])
        self.assertEqual(r["execution_issues"][1]["raw_value"], "88i")
        self.assertFalse(r["execution"])

    def test_result_header_does_not_leak_into_compiler_sections(self):
        body = b'"Selected Results Table"\nBenchmark,Base # Threads,Peak # Threads\n600.perlbench_s,64i,88i\nSPECspeed2017_int_base,12.9\n"Base Other Flags"\n600.perlbench_s,1,2\n'
        r = parse_disclosure(body, ".csv", "cpu2017", "speed")
        self.assertEqual(r["modes"]["base"]["unparsed_values"], ["64i"])
        self.assertEqual(len(r["execution_issues"]), 2)
        self.assertFalse(r["execution"])
