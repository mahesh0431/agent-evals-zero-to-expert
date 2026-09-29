# Capstone: evaluating a tool-using support agent with Inspect

Companion code for [Module 19 of Agent Evals: Zero to Expert](../../modules/19-capstone.html).

A small but complete agent eval: a customer-support agent with three tools
(`lookup_order`, `refund_order`, `escalate`) works on a toy order database. We grade
it three ways, run every task several times, and report pass@k, pass^k and
confidence intervals.

```
capstone/
├── support_eval.py   # the @task: dataset + scaffold (ReAct agent) + scorers + epochs
├── environment.py    # per-trial order DB (Inspect store) and the three @tool functions
├── scorers.py        # outcome (end state), policy (trajectory), reply_judge (LLM rubric)
├── data/
│   ├── orders.json   # seed database, reset before every trial
│   └── tasks.jsonl   # 12 tasks: input, target (what a good reply says), expected end state
├── smoke_test.py     # tests the EVAL with scripted mock agents (no API key needed)
├── analyze.py        # pass@k, pass^k, cluster-bootstrap CI, per-category table, failures
├── ci/agent-eval.yml # example GitHub Actions workflow
├── ci/gate.py        # exits 1 if pass^k falls below a floor
└── requirements.txt
```

## 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Tested with `inspect-ai` 0.3.272 on Python 3.11.

## 2. Check the eval itself first (free)

```bash
python smoke_test.py
```

This runs the whole pipeline on Inspect's `mockllm/model` provider with two
scripted "agents": a reference agent that follows the policy (must score 100% on
`outcome` and `policy`) and a sloppy one that refunds everything (must score
badly). If either assertion fails, a task or a grader is broken. Expected output:

```
reference  outcome=1.00  policy=1.00  reply_judge=1.00
sloppy     outcome=0.25  policy=0.00  reply_judge=1.00
Smoke test passed: the eval is solvable and discriminates.
```

(The judge is mocked in the smoke test, so its 1.00 means nothing there.)

## 3. Run it on a real model

Set the API key for your provider (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, ...), then:

```bash
# default: 4 epochs per task
inspect eval support_eval.py --model anthropic/<model-name>
inspect eval support_eval.py --model openai/<model-name>

# more epochs for tighter pass^k estimates
inspect eval support_eval.py --model anthropic/<model-name> -T epochs=8

# use a different (ideally stronger, fixed) model as the judge
inspect eval support_eval.py --model openai/<model-name> \
    --model-role grader=anthropic/<judge-model-name>

# quick iteration on a subset
inspect eval support_eval.py --model anthropic/<model-name> --limit 3 -T epochs=1
```

Replace `<model-name>` with a current model ID from your provider's docs.
If you do not bind a `grader` role, the judge falls back to the model under test,
which is cheaper but lets a model grade itself; avoid that for real decisions.

Inspect prints a table per scorer and reducer: `mean` (pass rate),
`pass_at_4` (at least one of 4 succeeds) and `pass_k_4` (all 4 succeed).

## 4. Read the transcripts

```bash
inspect view
```

Opens the log viewer in your browser. For each sample and epoch you can see the
full conversation, every tool call and result, and each scorer's explanation
(the policy scorer lists the exact step that broke a rule; the judge shows its
reasoning). Read failing transcripts before changing anything.

## 5. Compute the numbers you would report

```bash
python analyze.py                          # newest log in ./logs
python analyze.py logs/<file>.eval --k 1 2 4
python analyze.py logs/new.eval --baseline logs/old.eval   # paired comparison
python analyze.py --require outcome        # count success on outcome alone
```

A trial counts as a success when **both** `outcome` and `policy` pass (the judge is
reported separately because it is noisier). The script prints mean success with a
95% cluster-bootstrap CI (resampling tasks, not trials), pass@k and pass^k using the
unbiased estimators, a per-category table, and the list of failing trials.

With only 12 tasks the confidence interval is wide. That is the honest answer:
to detect small differences you need more tasks (see Module 04).

## 6. Put it in CI

`ci/agent-eval.yml` is an example workflow: run the smoke test on every PR, run the
real eval with a few epochs when prompts, tools or tasks change, and fail the build
if `pass^3` drops below a floor (`ci/gate.py`).

## Design choices worth copying

* **Fresh state per trial.** `init_db()` copies the seed DB into Inspect's per-sample
  store, so epochs and samples never leak state into each other.
* **The tools do not enforce the policy.** `refund_order` will happily refund an
  out-of-window order. Enforcing the policy is the agent's job, so that is what we test.
* **Grade the end state, not the words.** `outcome` reads the DB. An agent that says
  "refunded!" without calling the tool fails.
* **Grade the path separately.** `policy` catches "right answer, dangerous route"
  (refunding before looking up, touching another customer's order, repeat refunds).
* **Keep the judge narrow.** `reply_judge` only grades what code cannot: whether the
  reply is accurate *relative to the audit log* and has a good tone.
* **Test the eval.** `smoke_test.py` proves every task is solvable and that a bad agent
  scores badly, before you spend money on real runs.

## Ideas to extend it

* Add a simulated user (a second model playing the customer) for multi-turn tasks, as
  tau-bench does.
* Grow the dataset from real failures; add tags for difficulty and track per-tag trends.
* Add cost and latency: Inspect logs token usage per sample; report tokens per success.
* Calibrate the judge: hand-label 50 replies and measure agreement before trusting it.
