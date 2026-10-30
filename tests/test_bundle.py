import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_bundle.py"
spec = importlib.util.spec_from_file_location("check_bundle", SCRIPT)
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bundle-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.operator = self.root / "skills" / bundle.OPERATOR
        self.operator.mkdir(parents=True)
        for name in (bundle.OPERATOR, "sk-exam-plan"):
            folder = self.root / "skills" / name
            folder.mkdir(exist_ok=True)
            (folder / "SKILL.md").write_text(
                f'---\nname: {name}\ndescription: "Plan a real task"\n---\nBody\n', encoding="utf-8")
        original = self.operator / "upstream" / "example"
        original.mkdir(parents=True)
        (original / "SKILL.original.md").write_bytes(b"Original skill\n")
        (original / "LICENSE").write_bytes(b"MIT License\nCopyright example\n")
        self.lock = {
            "schema_version": 1, "version": "2.0.0",
            "sources": [{"id": "example", "repository": "owner/repo", "commit": "a" * 40,
                         "license": "MIT", "files": [
                             {"path": f"upstream/example/{name}", "source_path": source,
                              "sha256": hashlib.sha256((original / name).read_bytes()).hexdigest()}
                             for name, source in (("SKILL.original.md", "skills/plan/SKILL.md"),
                                                  ("LICENSE", "LICENSE"))]}],
            "skills": [{"name": bundle.OPERATOR, "path": f"skills/{bundle.OPERATOR}"},
                       {"name": "sk-exam-plan", "path": "skills/sk-exam-plan", "source_id": "example",
                        "entrypoint": "upstream/example/SKILL.original.md"}]
        }
        self.save()

    def save(self):
        (self.operator / "bundle-lock.json").write_text(json.dumps(self.lock), encoding="utf-8")

    def test_checkout_and_installed_layouts_have_same_counts(self):
        before = {str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.root.rglob("*") if p.is_file()}
        checkout = bundle.validate(self.root)
        installed = bundle.validate(self.root / "skills", installed=True)
        self.assertEqual(checkout["skills"], 2)
        self.assertEqual(checkout["routed_skills"], 1)
        self.assertEqual(checkout["source_files"], 2)
        self.assertEqual(installed["layout"], "installed")
        self.assertEqual(checkout["sources"], installed["sources"])
        after = {str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_tampered_original_is_rejected(self):
        (self.operator / "upstream/example/SKILL.original.md").write_bytes(b"Changed\n")
        with self.assertRaisesRegex(bundle.BundleError, "hash mismatch"):
            bundle.validate(self.root)

    def test_missing_source_or_skill_is_rejected(self):
        missing = self.root / "skills/sk-exam-plan/SKILL.md"
        missing.unlink()
        with self.assertRaisesRegex(bundle.BundleError, "missing file"):
            bundle.validate(self.root)
        missing.write_text("---\nname: sk-exam-plan\ndescription: Plan\n---\n", encoding="utf-8")
        (self.operator / "upstream/example/LICENSE").unlink()
        with self.assertRaisesRegex(bundle.BundleError, "missing file"):
            bundle.validate(self.root)

    def test_unsafe_paths_are_rejected_on_all_platforms(self):
        for unsafe in ("../outside", "/absolute", "C:/absolute", r"upstream\..\outside", "a/./b", "a//b"):
            with self.subTest(path=unsafe):
                self.lock["sources"][0]["files"][0]["path"] = unsafe
                self.save()
                with self.assertRaisesRegex(bundle.BundleError, "unsafe path"):
                    bundle.validate(self.root)

    def test_duplicate_skill_and_source_ids_are_rejected(self):
        self.lock["skills"].append(copy.deepcopy(self.lock["skills"][0]))
        self.save()
        with self.assertRaisesRegex(bundle.BundleError, "duplicate skill name"):
            bundle.validate(self.root)
        self.lock["skills"].pop()
        self.lock["sources"].append(copy.deepcopy(self.lock["sources"][0]))
        self.save()
        with self.assertRaisesRegex(bundle.BundleError, "duplicate source id"):
            bundle.validate(self.root)

    def test_unpinned_source_and_missing_license_are_rejected(self):
        self.lock["sources"][0]["commit"] = "main"
        self.save()
        with self.assertRaisesRegex(bundle.BundleError, "pinned"):
            bundle.validate(self.root)
        self.lock["sources"][0]["commit"] = "a" * 40
        self.lock["sources"][0]["files"].pop()
        self.save()
        with self.assertRaisesRegex(bundle.BundleError, "LICENSE is missing"):
            bundle.validate(self.root)

    def test_unknown_source_and_unlisted_route_are_rejected(self):
        self.lock["skills"][1]["source_id"] = "unknown"
        self.save()
        with self.assertRaisesRegex(bundle.BundleError, "unknown source_id"):
            bundle.validate(self.root)
        self.lock["skills"][1]["source_id"] = "example"
        self.lock["skills"][1]["entrypoint"] = "upstream/example/not-listed.md"
        self.save()
        with self.assertRaisesRegex(bundle.BundleError, "not in source manifest"):
            bundle.validate(self.root)

    def test_frontmatter_name_and_description_are_checked(self):
        path = self.root / "skills/sk-exam-plan/SKILL.md"
        for content, error in (("Body", "missing YAML"),
                               ("---\nname: other\ndescription: plan\n---\n", "name must"),
                               ("---\nname: sk-exam-plan\n---\n", "description"),
                               ("---\nname: sk-exam-plan\nname: sk-exam-plan\n---\n", "duplicate name")):
            with self.subTest(content=content):
                path.write_text(content, encoding="utf-8")
                with self.assertRaisesRegex(bundle.BundleError, error):
                    bundle.validate(self.root)

    def test_symlinked_source_is_rejected(self):
        source = self.operator / "upstream/example/SKILL.original.md"
        target = self.root / "outside-original.md"
        shutil.copyfile(source, target)
        source.unlink()
        try:
            source.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("Creating symlinks is unavailable on this platform")
        with self.assertRaisesRegex(bundle.BundleError, "symbolic links"):
            bundle.validate(self.root)

    def test_cli_returns_json_and_nonzero_on_failure(self):
        command = [sys.executable, "-B", str(SCRIPT), "--root", str(self.root)]
        success = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertEqual(json.loads(success.stdout)["status"], "ok")
        self.lock["schema_version"] = 99
        self.save()
        failure = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(failure.returncode, 1)
        self.assertIn("schema_version", json.loads(failure.stderr)["error"])


if __name__ == "__main__":
    unittest.main()
