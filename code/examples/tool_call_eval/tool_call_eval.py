"""Grade tool calls four ways, then A/B two tool-description variants.

Companion to Module 06 (tool use) and Module 24 (tools and MCP evals) of
Agent Evals: Zero to Expert. Standard library only, no API key, runs in < 1 s.

A deterministic mock agent answers 20 tasks by emitting tool calls. It
"understands" every request perfectly; its only mistakes come from what the
tool descriptions tell it (or fail to tell it). That isolates the one thing we
change between runs: the wording of the tool descriptions.

Each task is scored on four separate checks:

  selection  the right tools, no missing and no extra calls
  schema     every call is valid against its tool's JSON-style schema
  values     every expected call appears with exactly the expected arguments
  order      dependencies are respected (e.g. look up before you cancel)

A task passes only if all four pass. We then compute the pass rate with a
Wilson 95% interval and compare the two variants on the SAME tasks (paired):
a 2x2 table, an exact McNemar test and a paired bootstrap interval.

    python tool_call_eval.py
"""

from __future__ import annotations

import math
import random
import re
import sys

# --------------------------------------------------------------------------
# 1. Tools. Same names and parameters in both variants; only descriptions differ.
# --------------------------------------------------------------------------

SCHEMAS = {
    "get_order": {"order_id": {"type": "string", "pattern": r"^A\d{4}$", "required": True}},
    "get_customer": {"email": {"type": "string", "pattern": r"^[^@\s]+@[^@\s]+\.\w+$", "required": True}},
    "cancel_order": {
        "order_id": {"type": "string", "pattern": r"^A\d{4}$", "required": True},
        "reason": {"type": "string", "enum": ["customer_request", "duplicate", "fraud"], "required": True},
    },
    "search_flights": {
        "origin": {"type": "string", "pattern": r"^[A-Z]{3}$", "required": True},
        "destination": {"type": "string", "pattern": r"^[A-Z]{3}$", "required": True},
        "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$", "required": True},
    },
    "book_flight": {
        "flight_id": {"type": "string", "pattern": r"^FL\d{3}$", "required": True},
        "passenger_name": {"type": "string", "required": True},
    },
    "convert_currency": {
        "amount": {"type": "number", "required": True},
        "from_currency": {"type": "string", "pattern": r"^[A-Z]{3}$", "required": True},
        "to_currency": {"type": "string", "pattern": r"^[A-Z]{3}$", "required": True},
    },
    "get_weather": {
        "city": {"type": "string", "required": True},
        "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$", "required": False},
    },
}

# Variant A: terse descriptions, the kind that get written in five minutes.
DESC_A = {
    "get_order": "Get an order.",
    "get_customer": "Get a customer.",
    "cancel_order": "Cancel an order. reason: why.",
    "search_flights": "Search flights. date: the date.",
    "book_flight": "Book a flight.",
    "convert_currency": "Convert money between currencies.",
    "get_weather": "Weather for a city. date: the date.",
}

# Variant B: descriptions that say when to use the tool, formats, and prerequisites.
DESC_B = {
    "get_order": "Look up ONE order by its id (format A1234). Do not pass emails here.",
    "get_customer": "Find a customer account by email address. Use this whenever the user gives an email.",
    "cancel_order": "Cancel an order. Always call get_order first to confirm it exists and is cancellable. "
                    "reason must be one of: customer_request, duplicate, fraud.",
    "search_flights": "Search flights. origin/destination: 3-letter IATA codes. date: YYYY-MM-DD (ISO 8601).",
    "book_flight": "Book a flight. flight_id comes from search_flights results.",
    "convert_currency": "Convert an amount. from_currency/to_currency: ISO 4217 codes such as USD, EUR.",
    "get_weather": "Weather for a city. date (optional): YYYY-MM-DD (ISO 8601).",
}

# --------------------------------------------------------------------------
# 2. Tasks. `gold` is the expected call list. `said` maps canonical values to how
#    the user actually phrased them (the agent copies these when unsure of a format).
# --------------------------------------------------------------------------


def T(tid, prompt, gold, ordered=False, said=None, tags=()):
    return {"id": tid, "prompt": prompt, "gold": gold, "ordered": ordered, "said": said or {}, "tags": set(tags)}


TASKS = [
    T("t01", "Find flights SFO to JFK on March 3.",
      [("search_flights", {"origin": "SFO", "destination": "JFK", "date": "2026-03-03"})], said={"2026-03-03": "March 3"}),
    T("t02", "Any flights LAX to SEA on 2026-05-01?",
      [("search_flights", {"origin": "LAX", "destination": "SEA", "date": "2026-05-01"})]),
    T("t03", "Flights from BOS to ORD on the 14th of April please.",
      [("search_flights", {"origin": "BOS", "destination": "ORD", "date": "2026-04-14"})], said={"2026-04-14": "14th of April"}),
    T("t04", "What goes DEN to ATL on June 9?",
      [("search_flights", {"origin": "DEN", "destination": "ATL", "date": "2026-06-09"})], said={"2026-06-09": "June 9"}),
    T("t05", "I need a flight MIA to DFW next Friday.",  # 'today' is Wed 2026-03-18 in this toy world
      [("search_flights", {"origin": "MIA", "destination": "DFW", "date": "2026-03-20"})],
      said={"2026-03-20": "next Friday"}, tags=["relative_date"]),
    T("t06", "Weather in Lisbon on May 2?",
      [("get_weather", {"city": "Lisbon", "date": "2026-05-02"})], said={"2026-05-02": "May 2"}),
    T("t07", "Is it raining in Oslo right now?", [("get_weather", {"city": "Oslo"})]),
    T("t08", "How much is 250 dollars in euros?",
      [("convert_currency", {"amount": 250, "from_currency": "USD", "to_currency": "EUR"})],
      said={"USD": "dollars", "EUR": "euros"}),
    T("t09", "Convert 90 GBP to JPY.",
      [("convert_currency", {"amount": 90, "from_currency": "GBP", "to_currency": "JPY"})]),
    T("t10", "What is 1200 rupees in US dollars?",
      [("convert_currency", {"amount": 1200, "from_currency": "INR", "to_currency": "USD"})],
      said={"INR": "rupees", "USD": "US dollars"}),
    T("t11", "Pull up the account for jane@example.com.",
      [("get_customer", {"email": "jane@example.com"})], tags=["email_lookup"]),
    T("t12", "Which customer is li.wei@example.org?",
      [("get_customer", {"email": "li.wei@example.org"})], tags=["email_lookup"]),
    T("t13", "Check the account of omar@shop.io, he says he never got a receipt.",
      [("get_customer", {"email": "omar@shop.io"})], tags=["email_lookup"]),
    T("t14", "Cancel order A1042, the customer changed their mind.",
      [("get_order", {"order_id": "A1042"}), ("cancel_order", {"order_id": "A1042", "reason": "customer_request"})],
      ordered=True, said={"customer_request": "customer changed their mind"}, tags=["cancel"]),
    T("t15", "A2210 was placed twice by mistake, cancel it.",
      [("get_order", {"order_id": "A2210"}), ("cancel_order", {"order_id": "A2210", "reason": "duplicate"})],
      ordered=True, said={"duplicate": "placed twice by mistake"}, tags=["cancel"]),
    T("t16", "Cancel A3007, the card was stolen.",
      [("get_order", {"order_id": "A3007"}), ("cancel_order", {"order_id": "A3007", "reason": "fraud"})],
      ordered=True, said={"fraud": "card was stolen"}, tags=["cancel"]),
    T("t17", "Book FL204 (SFO to JFK, 2026-04-02) for Ana Ruiz.",
      [("book_flight", {"flight_id": "FL204", "passenger_name": "Ana Ruiz"})],
      said={"_route": ("SFO", "JFK", "2026-04-02")}, tags=["known_flight_id"]),
    T("t18", "Put Ken Sato on FL118 (ORD to LAX, 2026-04-09).",
      [("book_flight", {"flight_id": "FL118", "passenger_name": "Ken Sato"})],
      said={"_route": ("ORD", "LAX", "2026-04-09")}, tags=["known_flight_id"]),
    T("t19", "Status of order A5531?", [("get_order", {"order_id": "A5531"})]),
    T("t20", "Where is my order A0099?", [("get_order", {"order_id": "A0099"})]),
]

# --------------------------------------------------------------------------
# 3. The mock agent. Deterministic rules keyed on what the descriptions say.
# --------------------------------------------------------------------------


def mock_agent(task, desc):
    """Return the list of (tool, args) calls the agent makes for this task."""
    def knows(tool, hint):
        return hint.lower() in desc[tool].lower()

    calls = []
    for name, args in task["gold"]:
        args = dict(args)
        # Formats: without a stated format the agent copies the user's wording.
        if "date" in args and not knows(name, "YYYY-MM-DD"):
            args["date"] = task["said"].get(args["date"], args["date"])
        if "relative_date" in task["tags"] and knows(name, "YYYY-MM-DD"):
            args["date"] = "2026-03-27"  # formats it correctly but resolves 'next Friday' a week late
        for k in ("from_currency", "to_currency"):
            if k in args and not knows(name, "ISO 4217"):
                args[k] = task["said"].get(args[k], args[k])
        if "reason" in args and not knows(name, "one of"):
            args["reason"] = task["said"].get(args["reason"], args["reason"])
        # Tool choice: 'get a customer' vs 'get an order' is ambiguous for an email.
        if name == "get_customer" and not knows("get_customer", "email"):
            name, args = "get_order", {"order_id": args["email"]}
        # Prerequisites: only look up first if the description says so.
        if name == "get_order" and "cancel" in task["tags"] and not knows("cancel_order", "call get_order first"):
            continue
        # Over-eager: 'flight_id comes from search_flights' makes it search even with an id in hand.
        if name == "book_flight" and knows("book_flight", "comes from search_flights"):
            o, d, dt = task["said"]["_route"]
            calls.append(("search_flights", {"origin": o, "destination": d, "date": dt}))
        calls.append((name, args))
    return calls


# --------------------------------------------------------------------------
# 4. Graders.
# --------------------------------------------------------------------------


def schema_errors(name, args):
    if name not in SCHEMAS:
        return [f"unknown tool {name}"]
    errs, spec = [], SCHEMAS[name]
    for p, rule in spec.items():
        if rule["required"] and p not in args:
            errs.append(f"{name}.{p} missing")
    for p, v in args.items():
        rule = spec.get(p)
        if rule is None:
            errs.append(f"{name}.{p} not in schema")
            continue
        if rule["type"] == "number" and not isinstance(v, (int, float)):
            errs.append(f"{name}.{p} not a number")
        if rule["type"] == "string" and not isinstance(v, str):
            errs.append(f"{name}.{p} not a string")
        if "pattern" in rule and isinstance(v, str) and not re.match(rule["pattern"], v):
            errs.append(f"{p}={v!r} bad format")
        if "enum" in rule and v not in rule["enum"]:
            errs.append(f"{p}={v!r} not in enum")
    return errs


def is_subsequence(needle, hay):
    it = iter(hay)
    return all(x in it for x in needle)


def grade(task, calls):
    gold = task["gold"]
    names, gold_names = [c[0] for c in calls], [g[0] for g in gold]
    r = {
        "selection": sorted(names) == sorted(gold_names),
        "schema": all(not schema_errors(n, a) for n, a in calls),
        "values": all(any(n == gn and a == ga for n, a in calls) for gn, ga in gold),
        "order": (not task["ordered"]) or is_subsequence(gold_names, names),
    }
    r["pass"] = all(r.values())
    why = []
    if not r["selection"]:
        missing = [g for g in gold_names if names.count(g) < gold_names.count(g)]
        extra = [n for n in names if names.count(n) > gold_names.count(n)]
        why.append("tools" + "".join(f" -{m}" for m in dict.fromkeys(missing))
                   + "".join(f" +{e}" for e in dict.fromkeys(extra)))
    for n, a in calls:
        why += schema_errors(n, a)
    if r["schema"] and not r["values"]:
        for gn, ga in gold:
            got = next((a for n, a in calls if n == gn), {})
            why += [f"{k}={got.get(k)!r} != {v!r}" for k, v in ga.items() if got.get(k) != v]
    if not r["order"]:
        why.append("dependency order not respected")
    r["why"] = "; ".join(why)
    r["n_calls"], r["n_valid"] = len(calls), sum(not schema_errors(n, a) for n, a in calls)
    return r


# --------------------------------------------------------------------------
# 5. Statistics (plain Python).
# --------------------------------------------------------------------------


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, mid - half), min(1.0, mid + half))


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value from the discordant counts b and c."""
    n, k = b + c, min(b, c)
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def paired_bootstrap(a, b, iters=10_000, seed=0):
    rng, n, diffs = random.Random(seed), len(a), []
    for _ in range(iters):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(sum(b[i] - a[i] for i in idx) / n)
    diffs.sort()
    return diffs[int(0.025 * iters)], diffs[int(0.975 * iters) - 1]


# --------------------------------------------------------------------------
# 6. Report.
# --------------------------------------------------------------------------


def run_variant(desc):
    return [grade(t, mock_agent(t, desc)) for t in TASKS]


def summarize(label, results):
    n = len(results)
    k = sum(r["pass"] for r in results)
    lo, hi = wilson(k, n)
    calls = sum(r["n_calls"] for r in results)
    valid = sum(r["n_valid"] for r in results)
    print(f"  {label}")
    for m in ("selection", "schema", "values", "order"):
        print(f"    {m:<10} {sum(r[m] for r in results):>2}/{n} tasks")
    print(f"    schema-valid calls: {valid}/{calls}")
    print(f"    PASS RATE  {k}/{n} = {k / n:.0%}   Wilson 95% CI [{lo:.0%}, {hi:.0%}]")
    return k


def main():
    print("=" * 72)
    print("Tool-call eval: 20 tasks, mock agent, two tool-description variants")
    print("=" * 72)
    A, B = run_variant(DESC_A), run_variant(DESC_B)

    print("\nPer-task results (S=selection, J=schema, V=values, O=order; . = pass, x = fail)")
    print(f"  {'task':<5} {'A: SJVO':<9} {'B: SJVO':<9} {'why A failed':<36} why B failed")
    for t, a, b in zip(TASKS, A, B):
        fa = "".join("." if a[m] else "x" for m in ("selection", "schema", "values", "order"))
        fb = "".join("." if b[m] else "x" for m in ("selection", "schema", "values", "order"))
        wa = a["why"].split("; ")[0] if a["why"] else ""
        wb = b["why"].split("; ")[0] if b["why"] else ""
        print(f"  {t['id']:<5} {fa + (' ok' if a['pass'] else ' --'):<9} {fb + (' ok' if b['pass'] else ' --'):<9} {wa[:35]:<36} {wb[:35]}".rstrip())

    print("\nSummary")
    ka = summarize("A (terse descriptions)", A)
    kb = summarize("B (formats, when-to-use, prerequisites)", B)

    pa, pb = [int(r["pass"]) for r in A], [int(r["pass"]) for r in B]
    both = sum(x and y for x, y in zip(pa, pb))
    a_only = sum(x and not y for x, y in zip(pa, pb))
    b_only = sum(y and not x for x, y in zip(pa, pb))
    neither = len(pa) - both - a_only - b_only
    p = mcnemar_exact(a_only, b_only)
    lo, hi = paired_bootstrap(pa, pb)
    print("\nPaired comparison (same 20 tasks under both variants)")
    print("                 B pass   B fail")
    print(f"    A pass       {both:>5}    {a_only:>5}")
    print(f"    A fail       {b_only:>5}    {neither:>5}")
    print(f"    B - A = {(kb - ka) / len(TASKS):+.0%}  paired bootstrap 95% CI [{lo:+.0%}, {hi:+.0%}]")
    print(f"    exact McNemar p = {p:.4f}  (uses only the {a_only + b_only} discordant tasks)")
    print(f"    B fixed {b_only} tasks and broke {a_only}: read the broken ones before shipping B.")
    print("\nLesson: one pass/fail number hides WHY. Splitting selection / schema / values /")
    print("order shows that better descriptions fixed formats and tool choice, and that one")
    print("new sentence ('flight_id comes from search_flights') caused extra calls.")

    # Self-checks: the example must keep teaching what it claims.
    assert kb > ka, "variant B should beat A"
    assert a_only >= 1, "B should introduce at least one regression to discuss"
    assert p < 0.05, "the paired difference should be significant on these tasks"
    assert not A[1]["why"] and A[1]["pass"], "t02 (ISO date given) should pass under A"
    print("\nSelf-checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
