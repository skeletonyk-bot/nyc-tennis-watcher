#!/usr/bin/env python3
"""Zero-dependency test runner.

Runs every ``test_*`` function in ``tests/test_*.py`` without needing pytest.
(``pytest tests/`` also works if you have it installed.)

    python3 run_tests.py
"""

from __future__ import annotations

import importlib.util
import sys
import traceback
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent / "tests"


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    sys.path.insert(0, str(TESTS_DIR.parent))
    passed = failed = 0
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        module = load_module(path)
        for name in sorted(vars(module)):
            if not name.startswith("test_"):
                continue
            fn = getattr(module, name)
            if not callable(fn):
                continue
            try:
                fn()
                passed += 1
                print(f"PASS {path.name}::{name}")
            except Exception:
                failed += 1
                print(f"FAIL {path.name}::{name}")
                traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
