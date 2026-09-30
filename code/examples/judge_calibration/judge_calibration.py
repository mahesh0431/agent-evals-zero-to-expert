"""Calibrate an LLM judge against human labels, then correct its pass rate.

Companion to Module 03 (graders) and Module 13 (LLM-as-a-judge) of
Agent Evals: Zero to Expert. Standard library only, no API key, runs in ~1 s.

The story:
  1. Humans label 200 agent transcripts PASS/FAIL (the calibration set).
  2. A mock LLM judge labels the same 200. Its true error profile is fixed in
     code (it is lenient: it catches most passes but waves through many fails).
  3. We measure agreement, Cohen's kappa, and the judge's TPR and TNR.
  4. The judge then grades 1,000 new production transcripts that no human
     labeled. Its raw pass rate is biased. The Rogan-Gladen estimator removes
     that bias using TPR and TNR, and a bootstrap that resamples BOTH sets gives
     an honest interval.

Because this is a simulation we know the true production pass rate, so you can
see which estimate lands on it.

    python judge_calibration.py
"""

from __future__ import annotations

import math
import random
import sys

SEED = 13
TRUE_TPR = 0.92        # P(judge says PASS | human says PASS)
TRUE_TNR = 0.70        # P(judge says FAIL | human says FAIL)  -> a lenient judge
CAL_N, CAL_PASS = 200, 140           # calibration set: 70% pass per humans
PROD_N, PROD_TRUE_RATE = 1000, 0.55  # production set: hidden true pass rate
BOOT = 2000


def judge(human_pass: bool, rng: random.Random) -> bool:
    """The mock judge: a noisy, lenient classifier with known TPR/TNR."""
    return rng.random() < TRUE_TPR if human_pass else rng.random() >= TRUE_TNR


def confusion(human, judged):
    tp = sum(h and j for h, j in zip(human, judged))
    tn = sum((not h) and (not j) for h, j in zip(human, judged))
    fp = sum((not h) and j for h, j in zip(human, judged))
    fn = sum(h and (not j) for h, j in zip(human, judged))
    return tp, fp, fn, tn


def cohens_kappa(tp, fp, fn, tn):
    n = tp + fp + fn + tn
    po = (tp + tn) / n
    human_pass, judge_pass = (tp + fn) / n, (tp + fp) / n
    pe = human_pass * judge_pass + (1 - human_pass) * (1 - judge_pass)
    return 0.0 if pe == 1 else (po - pe) / (1 - pe)


def wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def rogan_gladen(p_obs, tpr, tnr):
    """True rate = (observed + TNR - 1) / (TPR + TNR - 1), clipped to [0, 1]."""
    youden = tpr + tnr - 1
    if youden <= 0:
        return float("nan")  # judge no better than chance: nothing to correct with
    return min(1.0, max(0.0, (p_obs + tnr - 1) / youden))


def bootstrap_rg(cal_cells, prod_judged, iters=BOOT, seed=SEED):
    """Resample calibration items (re-estimating TPR/TNR) and production items."""
    rng = random.Random(seed + 1)
    out = []
    for _ in range(iters):
        cells = rng.choices(cal_cells, k=len(cal_cells))
        tp, fn = cells.count("TP"), cells.count("FN")
        tn, fp = cells.count("TN"), cells.count("FP")
        if tp + fn == 0 or tn + fp == 0:
            continue
        tpr, tnr = tp / (tp + fn), tn / (tn + fp)
        p_obs = sum(rng.choices(prod_judged, k=len(prod_judged))) / len(prod_judged)
        est = rogan_gladen(p_obs, tpr, tnr)
        if not math.isnan(est):
            out.append(est)
    if len(out) < 100:
        return float("nan"), float("nan")  # judge too close to chance to correct
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out)) - 1]


def calibrate(human, judged):
    tp, fp, fn, tn = confusion(human, judged)
    cells = ["TP"] * tp + ["FP"] * fp + ["FN"] * fn + ["TN"] * tn
    return tp, fp, fn, tn, cells


def main():
    rng = random.Random(SEED)
    print("=" * 72)
    print("Judge calibration: 200 human labels, then 1,000 unlabeled production items")
    print("=" * 72)

    # ---- 1. calibration set -------------------------------------------------
    human = [True] * CAL_PASS + [False] * (CAL_N - CAL_PASS)
    rng.shuffle(human)
    judged = [judge(h, rng) for h in human]
    tp, fp, fn, tn, cells = calibrate(human, judged)
    tpr, tnr = tp / (tp + fn), tn / (tn + fp)
    agree = (tp + tn) / CAL_N
    kappa = cohens_kappa(tp, fp, fn, tn)

    print("\n1) Calibration set (n=200), judge vs human")
    print("                   human PASS  human FAIL")
    print(f"    judge PASS     {tp:>10}  {fp:>10}")
    print(f"    judge FAIL     {fn:>10}  {tn:>10}")
    lo, hi = wilson(tp, tp + fn)
    print(f"    TPR (sensitivity) = {tp}/{tp + fn} = {tpr:.3f}   95% CI [{lo:.3f}, {hi:.3f}]   (true {TRUE_TPR:.2f})")
    lo, hi = wilson(tn, tn + fp)
    print(f"    TNR (specificity) = {tn}/{tn + fp} = {tnr:.3f}   95% CI [{lo:.3f}, {hi:.3f}]   (true {TRUE_TNR:.2f})")
    print(f"    raw agreement     = {agree:.1%}")
    print(f"    Cohen's kappa     = {kappa:.3f}")
    print(f"    pass rate: humans {CAL_PASS / CAL_N:.1%}, judge {(tp + fp) / CAL_N:.1%}  (the judge is lenient)")

    # ---- 2. why kappa, not agreement ------------------------------------------
    k0 = cohens_kappa(CAL_PASS, CAL_N - CAL_PASS, 0, 0)
    print("\n2) Why report kappa: a useless judge that always says PASS")
    print(f"    raw agreement = {CAL_PASS / CAL_N:.1%}   Cohen's kappa = {k0:.3f}")
    print("    Agreement looks decent only because 70% of items pass. Kappa removes")
    print("    the agreement you would get by chance and exposes it.")

    # ---- 3. production set ----------------------------------------------------
    n_true_pass = round(PROD_N * PROD_TRUE_RATE)
    prod_truth = [True] * n_true_pass + [False] * (PROD_N - n_true_pass)
    rng.shuffle(prod_truth)
    prod_judged = [judge(h, rng) for h in prod_truth]  # humans never see these
    p_obs = sum(prod_judged) / PROD_N
    lo_obs, hi_obs = wilson(sum(prod_judged), PROD_N)
    rg = rogan_gladen(p_obs, tpr, tnr)
    lo_rg, hi_rg = bootstrap_rg(cells, prod_judged)

    print("\n3) Production set (n=1,000), judge only")
    print(f"    raw judge pass rate     {p_obs:.1%}   Wilson 95% CI [{lo_obs:.1%}, {hi_obs:.1%}]")
    print(f"    Rogan-Gladen corrected  {rg:.1%}   bootstrap 95% CI [{lo_rg:.1%}, {hi_rg:.1%}]")
    print(f"    TRUE pass rate (hidden) {PROD_TRUE_RATE:.1%}")
    print(f"    formula: ({p_obs:.3f} + {tnr:.3f} - 1) / ({tpr:.3f} + {tnr:.3f} - 1) = {rg:.3f}")
    if tpr + tnr - 1 < 0.3:
        print(f"    WARNING: TPR + TNR - 1 = {tpr + tnr - 1:.2f} is small; the correction is unstable.")
    print("    The raw interval is narrow AND wrong: more production data shrinks it")
    print("    around the biased value. Only the correction moves it to the truth,")
    print("    and its wider interval honestly includes the uncertainty in TPR/TNR.")

    # ---- 4. how many human labels? -------------------------------------------
    print("\n4) Same correction with fewer human labels (first k calibration items)")
    print(f"    {'labels':>6}  {'TPR':>6}  {'TNR':>6}  {'corrected':>9}  95% CI")
    for k in (40, 100, 200):
        tp_k, fp_k, fn_k, tn_k, cells_k = calibrate(human[:k], judged[:k])
        tpr_k, tnr_k = tp_k / (tp_k + fn_k), tn_k / (tn_k + fp_k)
        lo_k, hi_k = bootstrap_rg(cells_k, prod_judged)
        print(f"    {k:>6}  {tpr_k:>6.3f}  {tnr_k:>6.3f}  {rogan_gladen(p_obs, tpr_k, tnr_k):>9.1%}  [{lo_k:.1%}, {hi_k:.1%}]")
    print("    The fail class is the scarce one (30% of labels), so TNR is the noisy")
    print("    estimate. Spend extra labeling effort on likely failures.")

    # ---- self-checks -----------------------------------------------------------
    assert abs(k0) < 1e-12, "always-PASS judge must have kappa 0"
    assert not (lo_obs <= PROD_TRUE_RATE <= hi_obs), "raw judge CI should miss the truth (bias)"
    assert lo_rg <= PROD_TRUE_RATE <= hi_rg, "corrected CI should cover the truth"
    assert 0.4 < kappa < 0.8, "kappa should be moderate for this judge"
    print("\nSelf-checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
