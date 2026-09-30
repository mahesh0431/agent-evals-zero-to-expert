"""Execution accuracy vs exact match for text-to-SQL, on an in-memory SQLite DB.

Companion to Module 27 (domain playbook: data and analytics agents) of
Agent Evals: Zero to Expert. Standard library only (sqlite3), runs in < 1 s.

Ten questions, each with a gold SQL query and a "predicted" query from a mock
text-to-SQL agent. We grade every prediction four ways:

  EM         exact string match after light normalization (case, spaces, ';')
  EM-masked  the same, with literal values masked out. Spider's official exact
             match also ignores values (it compares parsed clauses); this is a
             simplified stand-in for that idea.
  EX         execution accuracy: run both queries, compare the result rows
             (as a multiset, or as an ordered list when gold has ORDER BY)
  EX-suite   EX on the main DB AND on a second DB with different contents, the
             idea behind "test-suite accuracy" (Zhong et al., EMNLP 2020)

The "truly correct" column is our own judgment of whether the SQL answers the
question for every possible database. Compare each metric with it.

    python text_to_sql_exec.py
"""

from __future__ import annotations

import re
import sqlite3
import sys
from collections import Counter

SCHEMA = """
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, country TEXT, signup_year INTEGER);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL, status TEXT, order_date TEXT);
"""

CUSTOMERS = [
    (1, "Ana", "US", 2021), (2, "Ben", "US", 2022), (3, "Chloe", "CA", 2024), (4, "Dev", "IN", 2025),
    (5, "Emma", "US", 2023), (6, "Farid", "CA", 2025), (7, "Gita", "IN", 2024), (8, "Hugo", "DE", 2025),
]
ORDERS = [
    (101, 1, 120.0, "shipped", "2025-02-10"), (102, 1, 40.0, "delivered", "2024-11-03"),
    (103, 2, 75.5, "shipped", "2025-06-21"), (104, 3, 310.0, "delivered", "2025-01-15"),
    (105, 3, 15.0, "cancelled", "2024-12-30"), (106, 4, 99.0, "shipped", "2025-03-02"),
    (107, 5, 210.0, "shipped", "2026-01-05"), (108, 5, 60.0, "delivered", "2025-12-31"),
    (109, 6, 45.0, "shipped", "2025-08-19"), (110, 2, 130.0, "cancelled", "2025-04-11"),
]
# The second DB for the test suite: same schema, a few extra rows chosen to
# separate queries that only agree by coincidence on the first DB.
EXTRA_CUSTOMERS = [(9, "Ivan", "CA", 2022)]
EXTRA_ORDERS = [(111, 9, 500.0, "shipped", "2023-07-01")]

# (question, gold SQL, predicted SQL, truly correct?, what it shows)
CASES = [
    ("How many customers are there?",
     "SELECT COUNT(*) FROM customers",
     "SELECT COUNT(*) FROM customers",
     True, "identical"),
    ("Names of customers in Canada.",
     "SELECT name FROM customers WHERE country = 'CA'",
     "SELECT c.name FROM customers AS c WHERE c.country = 'CA'",
     True, "alias only: EM misses a correct query"),
    ("Total revenue from shipped orders.",
     "SELECT SUM(amount) FROM orders WHERE status = 'shipped'",
     "SELECT SUM(amount) FROM orders WHERE status = 'delivered'",
     False, "wrong value: masked EM calls it correct"),
    ("Customers with an order over 100.",
     "SELECT DISTINCT c.name FROM customers c JOIN orders o ON o.customer_id = c.id WHERE o.amount > 100",
     "SELECT name FROM customers WHERE id IN (SELECT customer_id FROM orders WHERE amount > 100)",
     True, "JOIN vs subquery: same rows"),
    ("Ids of orders placed in 2025.",
     "SELECT id FROM orders WHERE order_date >= '2025-01-01' AND order_date < '2026-01-01'",
     "SELECT id FROM orders WHERE strftime('%Y', order_date) = '2025'",
     True, "date range vs strftime: same rows"),
    ("Average order amount per country, highest first.",
     "SELECT c.country, AVG(o.amount) AS a FROM orders o JOIN customers c ON c.id = o.customer_id "
     "GROUP BY c.country ORDER BY a DESC",
     "SELECT c.country, AVG(o.amount) FROM orders o JOIN customers c ON c.id = o.customer_id GROUP BY c.country",
     False, "right numbers, wrong order: EX checks order"),
    ("US customers who signed up before 2024.",
     "SELECT name FROM customers WHERE country = 'US' AND signup_year < 2024",
     "SELECT name FROM customers WHERE signup_year < 2024",
     False, "missing filter, right rows BY LUCK on DB 1"),
    ("Id of the most expensive order.",
     "SELECT id FROM orders ORDER BY amount DESC LIMIT 1",
     "SELECT id FROM orders WHERE amount = (SELECT MAX(amount) FROM orders)",
     True, "ORDER BY/LIMIT vs MAX subquery"),
    ("Number of orders per status.",
     "SELECT status, COUNT(*) FROM orders GROUP BY status",
     "SELECT status, COUNT(*) FROM orders GROUP status",
     False, "syntax error: fails to execute"),
    ("Customers who never ordered.",
     "SELECT name FROM customers WHERE id NOT IN (SELECT customer_id FROM orders)",
     "select name\n  from customers\n where id not in (select customer_id from orders);",
     True, "case and whitespace only: EM after normalizing"),
]


def make_db(extra: bool) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO customers VALUES (?,?,?,?)", CUSTOMERS + (EXTRA_CUSTOMERS if extra else []))
    con.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", ORDERS + (EXTRA_ORDERS if extra else []))
    return con


# ---------------------------------------------------------------- graders --

def normalize(sql: str, mask_values: bool = False) -> str:
    parts = re.split(r"('(?:[^']|'')*')", sql.strip().rstrip(";"))  # keep string literals intact
    out = []
    for i, p in enumerate(parts):
        if i % 2:  # a string literal
            out.append("'?'" if mask_values else p)
        else:
            p = p.lower()
            if mask_values:
                p = re.sub(r"\b\d+(\.\d+)?\b", "?", p)
            out.append(p)
    s = re.sub(r"\s+", " ", "".join(out))
    return re.sub(r"\s*([(),=<>*])\s*", r"\1", s).strip()


def exact_match(gold: str, pred: str, mask_values: bool = False) -> bool:
    return normalize(gold, mask_values) == normalize(pred, mask_values)


def run(con, sql):
    try:
        return con.execute(sql).fetchall(), None
    except sqlite3.Error as e:
        return None, str(e)


def same_result(gold_rows, pred_rows, ordered: bool) -> bool:
    if pred_rows is None:
        return False
    round_rows = lambda rows: [tuple(round(v, 6) if isinstance(v, float) else v for v in r) for r in rows]
    g, p = round_rows(gold_rows), round_rows(pred_rows)
    return g == p if ordered else Counter(g) == Counter(p)


def execution_match(con, gold, pred) -> tuple[bool, str | None]:
    gold_rows, err = run(con, gold)
    assert err is None, f"gold query failed: {err}"
    pred_rows, err = run(con, pred)
    ordered = re.search(r"\border\s+by\b", gold, re.I) is not None
    return same_result(gold_rows, pred_rows, ordered), err


# ----------------------------------------------------------------- report --

def main():
    db1, db2 = make_db(extra=False), make_db(extra=True)
    print("=" * 78)
    print("Text-to-SQL: exact match vs execution accuracy (SQLite, in memory)")
    print("=" * 78)
    print(f"\n  {'#':>2}  {'EM':<3} {'EMm':<3} {'EX':<3} {'EXs':<3} {'true':<4}  question / what it shows   (Y = graded correct)")
    rows = []
    for i, (q, gold, pred, truth, note) in enumerate(CASES, 1):
        em = exact_match(gold, pred)
        emm = exact_match(gold, pred, mask_values=True)
        ex1, err = execution_match(db1, gold, pred)
        ex2, _ = execution_match(db2, gold, pred)
        exs = ex1 and ex2
        rows.append((em, emm, ex1, exs, truth))
        mark = lambda b: "Y" if b else "."
        print(f"  {i:>2}  {mark(em):<3} {mark(emm):<3} {mark(ex1):<3} {mark(exs):<3} {mark(truth):<4}  {q}")
        print(f"{'':<27}-> {note}")
        if err:
            print(f"{'':<27}   sqlite error: {err}")
    n = len(rows)
    names = ["EM (strict)", "EM (values masked)", "EX (one DB)", "EX (test suite, 2 DBs)", "truly correct"]
    print("\nAccuracy")
    for j, name in enumerate(names):
        k = sum(r[j] for r in rows)
        wrong_yes = sum(r[j] and not r[4] for r in rows)
        wrong_no = sum((not r[j]) and r[4] for r in rows)
        extra = "" if j == 4 else f"   false accepts {wrong_yes}, false rejects {wrong_no}"
        print(f"  {name:<24} {k:>2}/{n} = {k / n:>4.0%}{extra}")

    print("\nWhy they differ")
    print("  * EM punishes harmless rewrites (aliases, JOIN vs IN, strftime vs ranges):")
    print("    SQL has many correct spellings, so EM under-counts correct answers.")
    print("  * Masking values (value-agnostic exact match, as in Spider's default")
    print("    exact-set match) does not help: it lets a wrong filter value")
    print("    ('delivered' for 'shipped') through (#3).")
    print("  * EX grades the answer, not the spelling, but a single small DB can make a")
    print("    wrong query return the right rows by luck (#7). Running on several DBs")
    print("    built to separate queries (a test suite) catches that.")
    print("  * EX must decide what 'same result' means: order matters only when the")
    print("    question asks for an order (#6); column names are ignored here.")

    em, emm, ex1, exs, truth = (sum(r[j] for r in rows) for j in range(5))
    assert (em, emm, ex1, exs, truth) == (2, 3, 7, 6, 6), (em, emm, ex1, exs, truth)
    assert all(r[3] == r[4] for r in rows), "the 2-DB suite should agree with the true labels"
    print("\nSelf-checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
