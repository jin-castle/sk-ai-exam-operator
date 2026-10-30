"""Include the distributed evidence guard tests in repository-wide checks."""
import importlib.util
from pathlib import Path

source = (Path(__file__).resolve().parents[1] / 'skills' / 'sk-ai-exam-operator'
          / 'tests' / 'test_evidence_guard.py')
spec = importlib.util.spec_from_file_location('distributed_evidence_guard_tests', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
GuardTests = module.GuardTests
