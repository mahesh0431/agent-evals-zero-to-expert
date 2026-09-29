"""Fail CI (exit 1) if reliability drops below a floor.

    python ci/gate.py logs/ci --min-pass-hat-k 0.8 --k 3
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analyze import load_trials, summarise  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("log_dir")
ap.add_argument("--k", type=int, default=3)
ap.add_argument("--min-pass-hat-k", type=float, default=0.8)
args = ap.parse_args()

newest = max(glob.glob(os.path.join(args.log_dir, "*.eval")), key=os.path.getmtime)
_, tasks = load_trials(newest, ["outcome", "policy"])
s = summarise(tasks, [args.k])
value = s[f"pass^{args.k}"]
print(f"pass^{args.k} = {value:.1%} (floor {args.min_pass_hat_k:.0%})")
sys.exit(0 if value >= args.min_pass_hat_k else 1)
