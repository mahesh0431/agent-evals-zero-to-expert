# Small runnable examples

Four self-contained eval examples that run offline in seconds. Each uses a
deterministic mock "agent" or "model", so there are no API keys, no downloads and no
cost, and the numbers are the same on every run. They complement the full
[capstone](../capstone), which evaluates a real model with Inspect.

Requirements: Python 3.9 or newer. Standard library only (`sqlite3` is part of it).

| Example | What it teaches | Modules | Run |
|---|---|---|---|
| [`tool_call_eval/`](tool_call_eval) | Grade tool calls on selection, schema, values and order; Wilson CI; paired A/B of two tool-description variants (McNemar, paired bootstrap) | [06](../../modules/06-tool-use-and-conversation.html), [24](../../modules/24-tools-and-mcp-evals.html) | `python tool_call_eval/tool_call_eval.py` |
| [`judge_calibration/`](judge_calibration) | Judge vs human labels: TPR, TNR, agreement, Cohen's kappa; Rogan-Gladen corrected pass rate with a bootstrap CI | [03](../../modules/03-graders.html), [13](../../modules/13-llm-as-judge.html) | `python judge_calibration/judge_calibration.py` |
| [`text_to_sql_exec/`](text_to_sql_exec) | Exact match vs execution accuracy on SQLite, and why a test suite of databases beats one database | [27](../../modules/27-domain-playbook.html) | `python text_to_sql_exec/text_to_sql_exec.py` |
| [`memory_probe/`](memory_probe) | Multi-session memory probes: recall, staleness after an update, abstention, deletion compliance plus a storage audit | [23](../../modules/23-memory-evals.html) | `python memory_probe/memory_probe.py` |

Run them all (exits non-zero if any example fails):

```bash
python run_all.py            # full reports, then a summary
python run_all.py --quiet    # summary only
```

Every example ends with self-checks (assertions) that the lesson it teaches still
holds, so `run_all.py` also works as a CI test for the examples. Each folder has its
own README with what to look at and a few experiments to try.

## How the mocks work

The point of these examples is the *grading and statistics*, so the systems under
test are simple and transparent:

* The tool-calling agent is a rule-based function whose mistakes are driven by what
  the tool descriptions say (formats, when to use a tool, prerequisites).
* The judge is a noisy classifier with a fixed true TPR and TNR, drawn with a seeded
  random generator, so the true pass rate is known and every estimate can be checked.
* The text-to-SQL "predictions" are hand-written queries, each chosen to show one
  way that string matching and execution matching disagree.
* The two memories are about 40 lines each: a keyword retriever over raw turns and a
  slot store where the latest value wins.

To evaluate a real system, keep the grader and statistics code and swap the mock for
calls to your agent or model.

## Expected output (abridged)

Output of `python run_all.py`; `[...]` marks omitted lines. Timings will vary.

```
##### tool_call_eval/tool_call_eval.py #####
========================================================================
Tool-call eval: 20 tasks, mock agent, two tool-description variants
[...]
Summary
  A (terse descriptions)
    selection  14/20 tasks
    schema      7/20 tasks
    values      7/20 tasks
    order      17/20 tasks
    schema-valid calls: 7/20
    PASS RATE  7/20 = 35%   Wilson 95% CI [18%, 57%]
  B (formats, when-to-use, prerequisites)
    selection  18/20 tasks
    schema     20/20 tasks
    values     19/20 tasks
    order      20/20 tasks
    schema-valid calls: 25/25
    PASS RATE  17/20 = 85%   Wilson 95% CI [64%, 95%]

Paired comparison (same 20 tasks under both variants)
                 B pass   B fail
    A pass           5        2
    A fail          12        1
    B - A = +50%  paired bootstrap 95% CI [+20%, +75%]
    exact McNemar p = 0.0129  (uses only the 14 discordant tasks)
    B fixed 12 tasks and broke 2: read the broken ones before shipping B.
[...]
Self-checks passed.

##### judge_calibration/judge_calibration.py #####
========================================================================
Judge calibration: 200 human labels, then 1,000 unlabeled production items
========================================================================

1) Calibration set (n=200), judge vs human
                   human PASS  human FAIL
    judge PASS            128          19
    judge FAIL             12          41
    TPR (sensitivity) = 128/140 = 0.914   95% CI [0.856, 0.950]   (true 0.92)
    TNR (specificity) = 41/60 = 0.683   95% CI [0.558, 0.787]   (true 0.70)
    raw agreement     = 84.5%
    Cohen's kappa     = 0.618
    pass rate: humans 70.0%, judge 73.5%  (the judge is lenient)
[...]
3) Production set (n=1,000), judge only
    raw judge pass rate     62.8%   Wilson 95% CI [59.8%, 65.7%]
    Rogan-Gladen corrected  52.1%   bootstrap 95% CI [37.0%, 62.4%]
    TRUE pass rate (hidden) 55.0%
    formula: (0.628 + 0.683 - 1) / (0.914 + 0.683 - 1) = 0.521
[...]
Self-checks passed.

##### text_to_sql_exec/text_to_sql_exec.py #####
==============================================================================
Text-to-SQL: exact match vs execution accuracy (SQLite, in memory)
==============================================================================
[...]
Accuracy
  EM (strict)               2/10 =  20%   false accepts 0, false rejects 4
  EM (values masked)        3/10 =  30%   false accepts 1, false rejects 4
  EX (one DB)               7/10 =  70%   false accepts 1, false rejects 0
  EX (test suite, 2 DBs)    6/10 =  60%   false accepts 0, false rejects 0
  truly correct             6/10 =  60%
[...]
Self-checks passed.

##### memory_probe/memory_probe.py #####
==============================================================================
Memory probes: 3 scripted sessions, 11 probes, 2 memory designs
==============================================================================
[...]
Scorecard (probes passed)
  category                 naive keyword     latest-wins
  recall                             3/4             4/4
  update                             0/2             2/2
  deletion                           1/2             2/2
  abstention                         0/2             2/2
  temporal                           1/1             0/1
  deletion (storage)                FAIL            pass
  stale answers                        2               0
[...]
Self-checks passed.

========================================
Summary
========================================
  PASS  tool_call_eval        0.13s
  PASS  judge_calibration     0.97s
  PASS  text_to_sql_exec      0.04s
  PASS  memory_probe          0.03s

4/4 examples passed.
```
