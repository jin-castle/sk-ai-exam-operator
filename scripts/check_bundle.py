#!/usr/bin/env python3
"""Checkout entrypoint for the checker also shipped inside the operator skill."""
from pathlib import Path
import runpy
import sys

CHECKER = Path(__file__).resolve().parents[1] / 'skills/sk-ai-exam-operator/scripts/check_bundle.py'
if __name__ == '__main__':
    if not any(arg in ('--root', '--installed-root') for arg in sys.argv[1:]):
        sys.argv.extend(['--root', str(Path(__file__).resolve().parents[1])])
    runpy.run_path(str(CHECKER), run_name='__main__')
else:
    globals().update(runpy.run_path(str(CHECKER)))
