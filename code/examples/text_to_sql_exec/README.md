# Text-to-SQL: exact match vs execution accuracy

Companion to [Module 27: Domain playbook](../../../modules/27-domain-playbook.html)
(data and analytics agents).

```bash
python text_to_sql_exec.py
```

Standard library only (`sqlite3`, in memory). No API key. Runs instantly.

## What it teaches

Ten questions over a tiny `customers` / `orders` database, each with a gold query and
a predicted query from a mock text-to-SQL agent. Each prediction is graded four ways
and compared with a "truly correct" label (does the SQL answer the question on every
possible database?).

| Metric | What it compares | Failure mode shown |
|---|---|---|
| EM (strict) | normalized SQL strings | rejects correct rewrites (aliases, JOIN vs IN, strftime vs date ranges) |
| EM (values masked) | normalized strings with literals masked | accepts a wrong filter value (`'delivered'` for `'shipped'`) |
| EX (one DB) | result rows of gold vs predicted | accepts a query that is right only by luck on this data |
| EX (test suite) | result rows on two different DBs | matches the true labels here |

Other details the script makes explicit:

* Results are compared as a multiset of rows, or as an ordered list when the gold
  query has `ORDER BY` (question 6 returns the right numbers in the wrong order).
* Column names are ignored; floats are rounded before comparison.
* A query that fails to execute (question 9) scores 0 on EX, with the SQLite error shown.

The test-suite idea comes from "Semantic Evaluation for Text-to-SQL with Distilled
Test Suites" (Zhong, Yu and Klein, EMNLP 2020), which builds many databases chosen
to separate near-miss queries. Two databases are enough to show the point here.

## Try this

The self-checks at the end of the script assert this exact setup, so some
experiments will trip them on purpose. Read the report above the assertion.

* Add a third question that is right by luck and a third database that exposes it.
* Make EX compare column names too. Which correct predictions would now fail?
* Put a `NULL` in `orders.customer_id` and rerun question 10: `NOT IN` with a `NULL`
  returns no rows, while the `LEFT JOIN ... IS NULL` version does not change. Which is
  "correct" now?
