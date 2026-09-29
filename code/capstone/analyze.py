"""Turn an Inspect log into the numbers you would actually report.

    python analyze.py                       # newest log in ./logs
    python analyze.py logs/run.eval --k 1 2 4
    python analyze.py logs/new.eval --baseline logs/old.eval   # paired comparison

What it prints
--------------
* Trial success = ALL of the chosen scorers passed (default: outcome AND policy).
  The judge is reported separately because it is noisier.
* pass@k  (at least one of k trials succeeds, unbiased estimator from the Codex paper)
* pass^k  (all k trials succeed, tau-bench's reliability metric)
* Mean success with a 95% CI from a *cluster* bootstrap: we resample TASKS, not
  trials, because trials of the same task are correlated.
* A per-category table and a list of failing trials to read first.

Only the standard library is used, so this runs anywhere Inspect runs.
"""

from __future__ import annotations

import argparse
import glob
import os
import random
import statistics
from collections import defaultdict
from math import comb

from inspect_ai.log import read_eval_log


# ----------------------------------------------------------------- estimators
def pass_at_k(n: int, c: int, k: int) -> float:
    """P(at least one of k draws succeeds) = 1 - C(n-c, k) / C(n, k)."""
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """P(all k draws succeed) = C(c, k) / C(n, k)."""
    return comb(c, k) / comb(n, k)


def cluster_bootstrap_ci(per_task: list[float], iters: int = 5000, seed: int = 0) -> tuple[float, float]:
    """95% CI for the mean of per-task success rates, resampling tasks."""
    rng = random.Random(seed)
    n = len(per_task)
    means = sorted(statistics.fmean(rng.choices(per_task, k=n)) for _ in range(iters))
    return means[int(0.025 * iters)], means[int(0.975 * iters) - 1]


# ----------------------------------------------------------------- loading
def load_trials(path: str, required: list[str]):
    """Return {task_id: [trial_dict, ...]} from one .eval log."""
    log = read_eval_log(path)
    if log.status != "success":
        print(f"warning: log status is {log.status}")
    tasks: dict[str, list[dict]] = defaultdict(list)
    for s in log.samples or []:
        scores = {name: sc.value for name, sc in (s.scores or {}).items()}
        ok = all(scores.get(r) == "C" for r in required)
        tasks[str(s.id)].append({
            "epoch": s.epoch,
            "success": ok,
            "judge": scores.get("reply_judge") == "C",
            "category": (s.metadata or {}).get("category", "?"),
            "failed": [name for name, v in scores.items() if v != "C"],
            "why": {name: (sc.explanation or "")[:140] for name, sc in (s.scores or {}).items() if sc.value != "C"},
        })
    return log, tasks


def summarise(tasks: dict[str, list[dict]], ks: list[int]) -> dict[str, float]:
    per_task = {t: statistics.fmean(tr["success"] for tr in trials) for t, trials in tasks.items()}
    out = {"mean": statistics.fmean(per_task.values())}
    for k in ks:
        valid = [(len(tr), sum(x["success"] for x in tr)) for tr in tasks.values() if len(tr) >= k]
        out[f"pass@{k}"] = statistics.fmean(pass_at_k(n, c, k) for n, c in valid)
        out[f"pass^{k}"] = statistics.fmean(pass_hat_k(n, c, k) for n, c in valid)
    out["ci_low"], out["ci_high"] = cluster_bootstrap_ci(list(per_task.values()))
    out["judge_pass"] = statistics.fmean(x["judge"] for tr in tasks.values() for x in tr)
    return out


# ----------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("log", nargs="?", help=".eval log file (default: newest in ./logs)")
    ap.add_argument("--k", type=int, nargs="+", default=[1, 2, 4])
    ap.add_argument("--require", nargs="+", default=["outcome", "policy"],
                    help="scorers that must all pass for a trial to count as a success")
    ap.add_argument("--baseline", help="second log for a paired, per-task comparison")
    args = ap.parse_args()

    path = args.log or max(glob.glob("logs/**/*.eval", recursive=True), key=os.path.getmtime)
    log, tasks = load_trials(path, args.require)
    n_trials = sum(len(v) for v in tasks.values())
    print(f"\n{log.eval.task} v{log.eval.task_version} | model {log.eval.model} | "
          f"{len(tasks)} tasks x {n_trials // max(len(tasks), 1)} epochs = {n_trials} trials")
    print(f"success = {' AND '.join(args.require)}\n")

    min_epochs = min(len(v) for v in tasks.values())
    args.k = [k for k in args.k if k <= min_epochs] or [1]  # k cannot exceed epochs run
    s = summarise(tasks, args.k)
    print(f"  mean success   {s['mean']:.1%}   95% CI [{s['ci_low']:.1%}, {s['ci_high']:.1%}] (cluster bootstrap)")
    for k in args.k:
        print(f"  pass@{k:<2d} {s[f'pass@{k}']:.1%}    pass^{k:<2d} {s[f'pass^{k}']:.1%}")
    print(f"  judge pass     {s['judge_pass']:.1%}  (reply accuracy + tone, model-graded)\n")

    # per-category breakdown: where do failures concentrate?
    by_cat: dict[str, list[bool]] = defaultdict(list)
    for trials in tasks.values():
        for x in trials:
            by_cat[x["category"]].append(x["success"])
    print("  category            n   success")
    for cat, v in sorted(by_cat.items(), key=lambda kv: statistics.fmean(kv[1])):
        print(f"  {cat:18s} {len(v):3d}   {statistics.fmean(v):.0%}")

    # failing trials: the reading list for error analysis
    print("\n  failing trials (read these transcripts in `inspect view` first):")
    if all(x["success"] for trials in tasks.values() for x in trials):
        print("   (none)")
    for t, trials in sorted(tasks.items()):
        for x in trials:
            if not x["success"]:
                reasons = "; ".join(f"{k}: {v}" for k, v in x["why"].items() if k in args.require)
                print(f"   - {t} epoch {x['epoch']}: {reasons}")

    if args.baseline:
        _, base = load_trials(args.baseline, args.require)
        shared = sorted(set(tasks) & set(base))
        diffs = [statistics.fmean(x["success"] for x in tasks[t]) - statistics.fmean(x["success"] for x in base[t])
                 for t in shared]
        lo, hi = cluster_bootstrap_ci(diffs)
        print(f"\n  paired difference vs baseline on {len(shared)} shared tasks: "
              f"{statistics.fmean(diffs):+.1%}  95% CI [{lo:+.1%}, {hi:+.1%}]")
        print("  (if the interval includes 0, you have not shown an improvement)")


if __name__ == "__main__":
    main()
