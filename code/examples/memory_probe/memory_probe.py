"""Probe two toy agent memories for recall, staleness, abstention and deletion.

Companion to Module 23 (evaluating agent memory) of Agent Evals: Zero to Expert.
Standard library only, no API key, runs in < 1 s.

A scripted user talks to an assistant over three sessions. Along the way they
plant facts, UPDATE one fact (they move city, they change diet), and ask the
assistant to FORGET one fact (their dog's name). After the last session we ask
probe questions, each with a known right answer, and grade two memories:

  NaiveKeywordMemory  stores every user turn verbatim; answers with the stored
                      turn that shares the most keywords with the question
                      (ties go to the oldest turn). Like top-1 retrieval, it
                      always returns something.
  LatestWinsMemory    extracts (slot, value) facts with simple patterns; a newer
                      value overwrites the old one; "forget X" deletes the slot;
                      it abstains when the slot is empty.

Probe categories and what "pass" means:

  recall       the answer contains the planted fact
  update       the answer contains the NEW value (containing only the old one = stale)
  deletion     the answer does not reveal the deleted value
  abstention   the answer is "I don't know" (the fact was never given)
  temporal     the answer uses history ("where did I live before ...?")

Plus a storage audit: after a deletion request, the deleted value must not be
anywhere in the memory store, whatever the probes say.

    python memory_probe.py
"""

from __future__ import annotations

import re
import sys

ABSTAIN = "I don't know."

SESSIONS = [
    ["Hi! My name is Maya.",
     "I live in Austin.",
     "I'm vegetarian.",
     "My dog is named Biscuit.",
     "Can you suggest a weekend hike?"],
    ["Quick update: I moved to Denver last month.",
     "My sister is called Priya.",
     "What's a good pasta recipe?",
     "I work as a nurse."],
    ["Please forget my dog's name.",
     "I'm allergic to peanuts.",
     "Update on my diet: I'm pescatarian now, not vegetarian."],
]

# (category, question, expected value or None, value that must NOT appear or None)
PROBES = [
    ("recall", "What is my name?", "Maya", None),
    ("recall", "What is my sister called?", "Priya", None),
    ("recall", "What do I do for work?", "nurse", None),
    ("recall", "Any food allergies I have?", "peanuts", None),
    ("update", "Where do I live?", "Denver", "Austin"),
    ("update", "Am I still vegetarian?", "pescatarian", "vegetarian"),
    ("deletion", "What's my dog called?", None, "Biscuit"),
    ("deletion", "What's my pet's name?", None, "Biscuit"),
    ("abstention", "What is my favorite color?", None, None),
    ("abstention", "What is my brother's name?", None, None),
    ("temporal", "Where did I live before Denver?", "Austin", None),
]
DELETED_VALUES = ["Biscuit"]

# ------------------------------------------------------------------ memories --

STOP = set("""i i'm me my is am are the a an what what's do did does to in of for any have
where who which how still you can please and now not on it at be so just quick update
last month hi good suggest""".split())


def keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z']+", text.lower())
    return {w.removesuffix("'s") for w in words if w not in STOP and w.removesuffix("'s") not in STOP}


class NaiveKeywordMemory:
    name = "naive keyword"

    def __init__(self):
        self.turns: list[str] = []

    def observe(self, text: str):
        self.turns.append(text)  # stores everything, including "please forget ..."

    def answer(self, question: str) -> str:
        q = keywords(question)
        best = max(range(len(self.turns)), key=lambda i: (len(q & keywords(self.turns[i])), -i))
        return self.turns[best]

    def dump(self) -> str:
        return " | ".join(self.turns)


class LatestWinsMemory:
    name = "latest-wins"
    WRITE = [
        (r"my name is (\w+)", "name"),
        (r"i (?:live|moved) (?:in|to) (\w+)", "city"),
        (r"i'm (vegetarian|vegan|pescatarian)\b", "diet"),
        (r"my dog is named (\w+)", "dog_name"),
        (r"my sister is called (\w+)", "sister"),
        (r"i work as an? (\w+)", "job"),
        (r"i'm allergic to (\w+)", "allergy"),
    ]
    FORGET = [(r"forget my dog'?s name", "dog_name")]
    # question keyword -> slot, checked in order (more specific first)
    READ = [("brother", "brother"), ("sister", "sister"), ("dog", "dog_name"), ("pet", "dog_name"),
            ("allerg", "allergy"), ("live", "city"), ("city", "city"), ("vegetarian", "diet"),
            ("diet", "diet"), ("work", "job"), ("job", "job"), ("color", "color"), ("name", "name")]

    def __init__(self):
        self.slots: dict[str, str] = {}

    def observe(self, text: str):
        low = text.lower()
        for pat, slot in self.FORGET:
            if re.search(pat, low):
                self.slots.pop(slot, None)
                return
        for pat, slot in self.WRITE:
            m = re.search(pat, text, re.I)
            if m:
                self.slots[slot] = m.group(1)  # newer overwrites older: history is lost

    def answer(self, question: str) -> str:
        low = question.lower()
        for kw, slot in self.READ:
            if kw in low:
                return self.slots.get(slot, ABSTAIN)
        return ABSTAIN

    def dump(self) -> str:
        return " | ".join(f"{k}={v}" for k, v in self.slots.items())


# ------------------------------------------------------------------- grading --

def has(text: str, value: str) -> bool:
    return re.search(rf"\b{re.escape(value)}\b", text, re.I) is not None


def grade(category, answer, expected, forbidden) -> tuple[bool, str]:
    if category == "abstention":
        return (answer == ABSTAIN, "abstained" if answer == ABSTAIN else "answered anyway")
    if category == "deletion":
        leaked = has(answer, forbidden)
        return (not leaked, "LEAKED" if leaked else "no leak")
    if category == "update":
        if has(answer, expected):
            return True, "current"
        return False, "STALE" if has(answer, forbidden) else "missing"
    ok = has(answer, expected)
    return ok, "found" if ok else ("abstained" if answer == ABSTAIN else "wrong")


def evaluate(memory):
    for s, session in enumerate(SESSIONS, 1):
        for turn in session:
            memory.observe(turn)
    rows = []
    for cat, q, exp, forb in PROBES:
        ans = memory.answer(q)
        ok, verdict = grade(cat, ans, exp, forb)
        rows.append((cat, q, ans, ok, verdict))
    store = memory.dump()
    audit_ok = not any(has(store, v) for v in DELETED_VALUES)
    return rows, audit_ok, store


# -------------------------------------------------------------------- report --

def main():
    print("=" * 78)
    print("Memory probes: 3 scripted sessions, 11 probes, 2 memory designs")
    print("=" * 78)
    print("\nScript (user turns):")
    for s, session in enumerate(SESSIONS, 1):
        for turn in session:
            print(f"  s{s}  {turn}")

    results = {}
    for mem in (NaiveKeywordMemory(), LatestWinsMemory()):
        rows, audit_ok, store = evaluate(mem)
        results[mem.name] = (rows, audit_ok)
        print(f"\n--- {mem.name} memory ---")
        for cat, q, ans, ok, verdict in rows:
            print(f"  {'PASS' if ok else 'FAIL'}  {cat:<10} {q:<33} -> {ans[:28]!r:<31} {verdict}")
        print(f"  {'PASS' if audit_ok else 'FAIL'}  storage audit: deleted value {'absent from' if audit_ok else 'STILL IN'} store")
        print(f"        store: {store[:66]}{'...' if len(store) > 66 else ''}")

    cats = ["recall", "update", "deletion", "abstention", "temporal"]
    print("\nScorecard (probes passed)")
    names = list(results)
    print(f"  {'category':<22}" + "".join(f"{n:>16}" for n in names))
    for c in cats:
        cells = []
        for n in names:
            rs = [r for r in results[n][0] if r[0] == c]
            cells.append(f"{sum(r[3] for r in rs)}/{len(rs)}")
        print(f"  {c:<22}" + "".join(f"{x:>16}" for x in cells))
    print(f"  {'deletion (storage)':<22}" + "".join(f"{('pass' if results[n][1] else 'FAIL'):>16}" for n in names))
    stale = {n: sum(r[4] == "STALE" for r in results[n][0]) for n in names}
    print(f"  {'stale answers':<22}" + "".join(f"{stale[n]:>16}" for n in names))

    print("\nWhat to notice")
    print("  * The naive memory never abstains: retrieval always returns SOMETHING, so")
    print("    'never told' questions get confident wrong answers.")
    print("  * It serves stale facts: 'I live in Austin' matches 'live'; the update")
    print("    'I moved to Denver' does not share the keyword.")
    print("  * Exact keywords miss paraphrases: 'allergies' never matches 'allergic'.")
    print("  * Its 'pet' deletion probe passes by luck, but the storage audit shows")
    print("    'Biscuit' is still stored. Probe answers AND audit the store.")
    print("  * Latest-wins fixes staleness, abstention and deletion, but overwriting")
    print("    destroys history, so it fails the temporal probe. Keep dated history")
    print("    (valid-from / valid-to) if users ask about the past. (Naive passes it only")
    print("    because ties go to the oldest turn.)")
    print("  * Latest-wins' patterns were written for THIS script, so its perfect")
    print("    recall is optimistic. Probe with held-out phrasings before trusting it.")

    naive_rows, naive_audit = results["naive keyword"]
    lw_rows, lw_audit = results["latest-wins"]
    assert not naive_audit and lw_audit, "storage audit should separate the two designs"
    assert stale["naive keyword"] == 2 and stale["latest-wins"] == 0
    assert all(r[3] for r in lw_rows if r[0] != "temporal") and not any(r[3] for r in lw_rows if r[0] == "temporal")
    assert not any(r[3] for r in naive_rows if r[0] == "abstention")
    print("\nSelf-checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
