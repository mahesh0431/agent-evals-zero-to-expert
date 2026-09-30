# Judge calibration: kappa and the Rogan-Gladen correction

Companion to [Module 03: Graders](../../../modules/03-graders.html) and
[Module 13: LLM-as-a-judge](../../../modules/13-llm-as-judge.html).

```bash
python judge_calibration.py
```

Standard library only. No API key. Runs in about a second (a 2,000-draw bootstrap).

## What it teaches

A mock LLM judge with a known error profile (true TPR 0.92, true TNR 0.70, so it is
lenient) grades 200 transcripts that humans also labeled, then 1,000 production
transcripts that no human saw. Because this is a simulation, the true production
pass rate (55%) is known, so you can check every estimate against it.

* **Measure the judge against humans first.** Confusion matrix, TPR, TNR (each with a
  Wilson interval), raw agreement and Cohen's kappa.
* **Why kappa and not agreement.** A judge that always says PASS agrees with humans
  70% of the time on this data and has kappa exactly 0.
* **A biased judge gives a biased pass rate, and more data does not help.** The raw
  judge pass rate on production has a narrow interval that misses the truth.
* **Correct it.** The Rogan-Gladen estimator,
  `true = (observed + TNR - 1) / (TPR + TNR - 1)`, moves the estimate back to the
  truth. It needs TPR + TNR > 1 (a judge better than chance).
* **Honest intervals resample both sets.** The bootstrap re-estimates TPR and TNR from
  resampled calibration labels AND resamples the production verdicts, so the
  interval includes the uncertainty from having only 200 human labels.
* **How many labels?** With 40 labels the corrected interval is very wide; the scarce
  FAIL class makes TNR the noisy estimate.

## Try this

The self-checks at the end of the script assert this exact setup, so some
experiments will trip them on purpose. Read the report above the assertion.

* Set `TRUE_TNR = 0.55` (a very lenient judge) and watch the correction's interval widen.
* Set `TRUE_TPR = 0.5, TRUE_TNR = 0.5`: the judge is a coin flip. The denominator
  TPR + TNR - 1 is then close to 0, so small sampling errors in TPR and TNR blow the
  estimate up and the interval covers most of [0, 1]. There is nothing to correct with
  (if the estimated TPR + TNR - 1 is 0 or below, the estimator returns NaN).
* Change `PROD_TRUE_RATE`: the correction still works when production has a different
  pass rate than the calibration set, as long as TPR and TNR stay the same. If the
  judge's error rates shift too (new kinds of transcripts), recalibrate.
