import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from cpushowspeed.timeline_html import render_html


class TimelineHTMLTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node required for offline JavaScript interaction checks")
    def test_generated_interactions(self):
        rows = []
        for i, (name, value, yr) in enumerate(
            [("High machine", 10, 1990), ("Low machine", 2, 1980), ("Overlap machine", 2, 1980), ("Unknown machine", 5, "")]
        ):
            rows.append(
                dict(
                    configuration_id=str(i),
                    system=name,
                    vaxen=value,
                    ci95_low=value / 2,
                    ci95_high=value * 2,
                    year=yr,
                    year_low=yr,
                    year_high=yr,
                    route="classical",
                    cpu="CPU",
                    clock_mhz=10,
                    os="",
                    configuration="",
                    scores="{}",
                    date_method="estimated",
                    source_url="https://example.com",
                    date_sources="",
                    date_notes="",
                )
            )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "timeline.html"
            render_html(rows, path)
            subprocess.run(["node", "tests/timeline_interaction.js", str(path)], check=True, capture_output=True, text=True)

    def test_chart_height_contract(self):
        from cpushowspeed.timeline_html import PAGE

        self.assertIn("75svh - 80px", PAGE)
        self.assertNotIn('type="range"', PAGE)
        for width, height in [(1920, 1080), (2560, 1440), (1366, 768), (390, 844)]:
            chart_width = min(width - 48, 1440, (height * 0.75 - 80) * 1400 / 760)
            self.assertLessEqual(chart_width * 760 / 1400 + 80, height * 0.75 + 0.01)

    def test_retro_themes_are_scoped_and_self_contained(self):
        import re

        from cpushowspeed import timeline_retro, timeline_theme

        css = timeline_theme.stylesheet()
        for value in ("win98", "system7", "vt220"):
            self.assertIn(f':root[data-theme="{value}"] body', css)
            self.assertIn(f'value="{value}"', timeline_theme.picker())
        # A window rule applied to body must not clip it: body overflow would stop the page scrolling.
        for value in ("win98", "system7", "vt220"):
            overflow = re.findall(rf':root\[data-theme="{value}"\] body\{{[^}}]*?overflow:\s*(\w+)', css)
            self.assertIn(overflow[-1:], ([], ["visible"]), value)
        self.assertNotIn("svg-load(", css)
        self.assertIsNone(re.search(r'url\((?!"data:)', css))
        with self.assertRaises(ValueError):
            timeline_retro.take(timeline_retro.WIN98, ["no-such-selector"], ":root")

    def test_payload_cannot_close_script(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "timeline.html"
            render_html([{"system": "</script><script>alert(1)</script>"}], path)
            html = path.read_text()
            # The theme initialiser, the worker source and the page code.
            self.assertEqual(html.count("</script>"), 3)
            self.assertNotIn("alert(1)", html)
            self.assertNotIn("<script src=", html)
            self.assertFalse((path.parent / "assets").exists())
            self.assertIn("Copyright", html)
            self.assertTrue((path.parent / "data/timeline.parquet").is_file())
