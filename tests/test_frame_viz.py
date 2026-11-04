import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "skills" / "sk-exam-frame" / "scripts" / "frame_viz.py"
spec = importlib.util.spec_from_file_location("frame_viz", SCRIPT)
viz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(viz)


def rects(svg):
    root = ET.fromstring(svg)
    return [(float(r.get("x")), float(r.get("y")), float(r.get("width")), float(r.get("height")))
            for r in root.iter("{http://www.w3.org/2000/svg}rect") if r.get("rx")]


class FrameVizTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="frame-viz-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-X", "utf8", "-B", str(SCRIPT), *map(str, args)],
                              capture_output=True, encoding="utf-8")

    def test_template_then_map_is_valid_svg_with_escaped_text(self):
        spec_path = self.root / "map.json"
        self.assertEqual(self.run_cli("template", "--out", spec_path).returncode, 0)
        data = json.loads(spec_path.read_text(encoding="utf-8"))
        data["problem"] = "A < B & C > D 인 경우"
        spec_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        out = self.root / "map.svg"
        result = self.run_cli("map", spec_path, "--out", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        svg = out.read_text(encoding="utf-8")
        ET.fromstring(svg)  # well-formed XML
        self.assertIn("A &lt; B &amp; C &gt; D", svg)
        self.assertEqual(json.loads(result.stdout)["assumptions"], 1)

    def test_assumption_origin_is_shown(self):
        svg, _ = viz.draw_map({"problem": "p", "assumptions": [
            {"assumption": "a", "breaks": "b", "question": "q", "status": "미확인", "by": "AI 제안"},
            {"assumption": "c", "breaks": "d", "question": "r", "status": "확인"}]})
        self.assertIn("[미확인 · AI 제안]", svg)
        self.assertIn("[확인]", svg)

    def test_template_does_not_overwrite(self):
        spec_path = self.root / "map.json"
        spec_path.write_text("keep", encoding="utf-8")
        self.assertEqual(self.run_cli("template", "--out", spec_path).returncode, 1)
        self.assertEqual(spec_path.read_text(encoding="utf-8"), "keep")

    def test_assumption_rows_do_not_overlap(self):
        long = "아주 긴 문장 " * 12
        svg, _ = viz.draw_map({"problem": "p", "assumptions": [
            {"assumption": long, "breaks": "짧음", "question": "짧음", "status": "미확인"},
            {"assumption": "짧음", "breaks": long, "question": long, "status": "확인"}]})
        boxes = sorted(rects(svg), key=lambda r: (r[0], r[1]))
        for a, b in zip(boxes, boxes[1:]):
            if a[0] == b[0]:
                self.assertLessEqual(a[1] + a[3], b[1] + 0.01, (a, b))

    def test_empty_spec_is_nothing_to_draw(self):
        spec_path = self.root / "empty.json"
        spec_path.write_text("{}", encoding="utf-8")
        result = self.run_cli("map", spec_path, "--out", self.root / "x.svg")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.root / "x.svg").exists())

    def test_scatter_counts_skipped_and_outliers(self):
        csv_path = self.root / "points.csv"
        rows = ["x,y,g"] + [f"{i % 10},{i // 10},{'a' if i % 2 else 'b'}" for i in range(200)]
        rows += [",3,a", "abc,1,b", "5000,5000,a"]  # missing, non-numeric, unit outlier
        csv_path.write_text("\n".join(rows), encoding="utf-8")
        out = self.root / "s.svg"
        result = self.run_cli("scatter", csv_path, "--x", "x", "--y", "y", "--group", "g",
                              "--mark", "0,0:origin", "--out", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["rows_read"], 203)
        self.assertEqual(summary["skipped_non_numeric"], 2)
        self.assertEqual(summary["outside_view"], 1)
        self.assertEqual(summary["plotted"], 200)
        self.assertEqual(sum(summary["groups"].values()), 201)
        ET.fromstring(out.read_text(encoding="utf-8"))

    def test_scatter_errors(self):
        csv_path = self.root / "points.csv"
        csv_path.write_text("x,y\n,\n", encoding="utf-8")
        missing_col = self.run_cli("scatter", csv_path, "--x", "lon", "--y", "y", "--out", self.root / "a.svg")
        self.assertEqual(missing_col.returncode, 1)
        self.assertIn("lon", json.loads(missing_col.stderr)["error"])
        nothing = self.run_cli("scatter", csv_path, "--x", "x", "--y", "y", "--out", self.root / "b.svg")
        self.assertEqual(nothing.returncode, 2)
        bad_mark = self.run_cli("scatter", csv_path, "--x", "x", "--y", "y", "--mark", "zero", "--out",
                                self.root / "c.svg")
        self.assertEqual(bad_mark.returncode, 1)

    def test_wrap_respects_width(self):
        for text in ("한글과 English mixed 문장이 길게 이어지는 경우", "띄어쓰기없이아주길게이어지는한국어문장입니다"):
            for line in viz.wrap(text, 120, 13):
                self.assertLessEqual(viz.text_width(line, 13), 120 + 1e-9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
