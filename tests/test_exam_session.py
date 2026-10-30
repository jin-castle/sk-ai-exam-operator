import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
WORK = REPOSITORY / "work"
WORK.mkdir(exist_ok=True)
SKILL = REPOSITORY / "skills" / "sk-ai-exam-operator"
SCRIPT = SKILL / "scripts" / "exam_session.py"
spec = importlib.util.spec_from_file_location("exam_session", SCRIPT)
operator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(operator)


def snapshot(root):
    return {str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in root.rglob("*") if path.is_file()}


class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="operator-test-", dir=WORK)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "notes"

    def test_time_contract_at_every_transition(self):
        expected = {
            180: "inspect", 172: "interview", 160: "rules", 150: "plan",
            140: "prototype", 115: "test", 100: "improve", 75: "complete-flow",
            55: "review", 35: "explain", 15: "final", 0: "expired",
        }
        for remaining, stage in expected.items():
            with self.subTest(remaining=remaining):
                self.assertEqual(operator.window_for(remaining)["id"], stage)
        self.assertEqual(operator.window_for(15.01)["id"], "explain")
        self.assertEqual(operator.window_for(0.01)["id"], "final")

    def test_unknown_time_is_not_assumed_to_be_180(self):
        result = operator.session("init", self.root)
        self.assertIsNone(result["last_reported_remaining"])
        self.assertEqual(result["advisory_window"]["id"], "unconfirmed")
        self.assertEqual(result["time_source"], "unconfirmed")
        self.assertIn("미확인", (self.root / "00_status.md").read_text(encoding="utf-8"))

    def test_checkpoint_without_new_report_keeps_time_and_provenance(self):
        first = operator.session("init", self.root, 72)
        before = (self.root / ".operator-state.json").read_bytes()
        result = operator.session("checkpoint", self.root)
        self.assertEqual(result["last_reported_remaining"], 72)
        self.assertFalse(result["new_user_report_recorded"])
        self.assertEqual(result["reported_at_utc"], first["reported_at_utc"])
        self.assertEqual((self.root / ".operator-state.json").read_bytes(), before)

    def test_repeated_initialization_resumes_and_preserves_all_notes(self):
        operator.session("init", self.root, 72)
        expected = {}
        for name in operator.NOTES:
            path = self.root / name
            path.write_text("# 참가자의 기존 기록\n\n수정하지 말 것: " + name, encoding="utf-8")
            expected[name] = path.read_bytes()
        result = operator.session("init", self.root)
        self.assertEqual(result["last_reported_remaining"], 72)
        for name, content in expected.items():
            self.assertEqual((self.root / name).read_bytes(), content)
        operator.session("checkpoint", self.root, 12)
        for name, content in expected.items():
            self.assertEqual((self.root / name).read_bytes(), content)

    def test_existing_domain_note_is_not_replaced(self):
        self.root.mkdir()
        original = b"existing unstructured user notes"
        (self.root / "01_domain.md").write_bytes(original)
        operator.session("init", self.root, 140)
        self.assertEqual((self.root / "01_domain.md").read_bytes(), original)
        self.assertTrue((self.root / "05_verification.md").is_file())

    def test_user_time_correction_can_increase_without_restarting(self):
        operator.session("init", self.root, 72)
        result = operator.session("checkpoint", self.root, 100)
        self.assertTrue(result["time_increased_by_user_correction"])
        self.assertEqual(result["last_reported_remaining"], 100)
        self.assertEqual(result["advisory_window"]["id"], "improve")

    def test_invalid_remaining_does_not_create_or_change_files(self):
        for value in (-1, 181, math.nan, math.inf, True, "72"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    operator.session("init", self.root, value)
                self.assertFalse(self.root.exists())
        operator.session("init", self.root, 72)
        before = snapshot(self.root)
        with self.assertRaises(ValueError):
            operator.session("checkpoint", self.root, -1)
        self.assertEqual(snapshot(self.root), before)

    def test_unowned_status_is_preserved_without_partial_initialization(self):
        self.root.mkdir()
        (self.root / "00_status.md").write_text("# User status\nkeep", encoding="utf-8")
        before = snapshot(self.root)
        with self.assertRaises(ValueError):
            operator.session("init", self.root, 72)
        self.assertEqual(snapshot(self.root), before)

    def test_corrupt_and_foreign_states_are_preserved(self):
        self.root.mkdir()
        for content in ("{broken-json", json.dumps({"owner": "someone-else", "schema_version": 1})):
            with self.subTest(content=content):
                (self.root / ".operator-state.json").write_text(content, encoding="utf-8")
                before = snapshot(self.root)
                with self.assertRaises(ValueError):
                    operator.session("init", self.root, 72)
                self.assertEqual(snapshot(self.root), before)

    def test_invalid_persisted_timer_is_preserved(self):
        operator.session("init", self.root, 72)
        path = self.root / ".operator-state.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["timer"]["last_reported_remaining"] = -5
        path.write_text(json.dumps(state), encoding="utf-8")
        before = snapshot(self.root)
        with self.assertRaises(ValueError):
            operator.session("checkpoint", self.root, 70)
        self.assertEqual(snapshot(self.root), before)

    def test_missing_checkpoint_does_not_start_a_new_session(self):
        with self.assertRaises(ValueError):
            operator.session("checkpoint", self.root, 72)
        self.assertFalse(self.root.exists())

    def test_status_is_read_only(self):
        operator.session("init", self.root, 72)
        before = snapshot(self.root)
        result = operator.session("status", self.root)
        self.assertEqual(result["advisory_window"]["id"], "complete-flow")
        self.assertEqual(snapshot(self.root), before)

    def test_note_directory_collision_is_preserved(self):
        (self.root / "01_domain.md").mkdir(parents=True)
        with self.assertRaises(ValueError):
            operator.session("init", self.root, 72)
        self.assertFalse((self.root / ".operator-state.json").exists())
        self.assertTrue((self.root / "01_domain.md").is_dir())

    def test_linked_note_is_not_followed(self):
        self.root.mkdir()
        external = Path(self.temporary.name) / "original.md"
        external.write_text("preserve", encoding="utf-8")
        try:
            (self.root / "01_domain.md").symlink_to(external)
        except OSError:
            self.skipTest("host does not permit creating test symlinks")
        with self.assertRaises(ValueError):
            operator.session("init", self.root, 72)
        self.assertEqual(external.read_text(encoding="utf-8"), "preserve")
        self.assertFalse((self.root / ".operator-state.json").exists())

    def test_cli_reports_valid_json_and_rejects_invalid_time(self):
        command = [sys.executable, "-X", "utf8", "-B", str(SCRIPT)]
        result = subprocess.run(command + ["init", "--root", str(self.root), "--remaining", "12"],
                                capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["advisory_window"]["id"], "final")
        before = snapshot(self.root)
        invalid = subprocess.run(command + ["checkpoint", "--root", str(self.root), "--remaining", "nan"],
                                 capture_output=True, encoding="utf-8")
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("error", json.loads(invalid.stderr))
        self.assertEqual(snapshot(self.root), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
