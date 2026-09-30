"""Run every example and exit non-zero if any of them fails.

Each example ends with self-checks (asserts) that the lesson it teaches still
holds, so this doubles as a test suite for the examples themselves.

    python run_all.py            # full output of every example, then a summary
    python run_all.py --quiet    # summary only
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXAMPLES = [
    ("tool_call_eval", "tool_call_eval.py"),
    ("judge_calibration", "judge_calibration.py"),
    ("text_to_sql_exec", "text_to_sql_exec.py"),
    ("memory_probe", "memory_probe.py"),
]


def main() -> int:
    quiet = "--quiet" in sys.argv
    results = []
    for folder, script in EXAMPLES:
        path = HERE / folder / script
        t0 = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, str(path)], cwd=path.parent, capture_output=True, text=True, timeout=120
        )
        dt = time.perf_counter() - t0
        ok = proc.returncode == 0 and "Self-checks passed." in proc.stdout
        results.append((folder, ok, dt))
        if not quiet or not ok:
            print(f"\n##### {folder}/{script} #####")
            print(proc.stdout.rstrip())
            if proc.stderr.strip():
                print(proc.stderr.rstrip())

    print("\n" + "=" * 40)
    print("Summary")
    print("=" * 40)
    for folder, ok, dt in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {folder:<20} {dt:5.2f}s")
    failed = [f for f, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} examples passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
