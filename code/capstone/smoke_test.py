"""Test the eval itself, with no API keys and no cost.

Before trusting an eval on a real model, check two things (Anthropic's
"Demystifying evals for AI agents" recommends reference solutions for the
same reason):

  1. It is SOLVABLE: a scripted agent that follows the policy scores 100% on the
     code-based graders. If it doesn't, a task or a grader is broken.
  2. It DISCRIMINATES: a scripted sloppy agent scores badly. If it doesn't, the
     graders are too lenient.

Both "agents" run on Inspect's mockllm provider, which lets us script the model's
outputs with a Python function. The judge is mocked too, so the judge's verdict
here is meaningless; we only check that the pipeline runs.

    python smoke_test.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from inspect_ai import eval  # noqa: A004,E402
from inspect_ai.model import (  # noqa: E402
    ChatMessageAssistant,
    ChatMessageTool,
    ChatMessageUser,
    ModelOutput,
    ModelUsage,
    get_model,
)

from support_eval import support_eval  # noqa: E402

ORDER_RE = re.compile(r"\bA\d{4}\b")


def _first_user_text(messages) -> str:
    return next(m.text for m in messages if isinstance(m, ChatMessageUser))


def _calls_made(messages) -> list[tuple[str, str]]:
    out = []
    for m in messages:
        if isinstance(m, ChatMessageAssistant) and m.tool_calls:
            out += [(c.function, c.arguments.get("order_id", "")) for c in m.tool_calls]
    return out


def _lookups(messages) -> dict[str, dict | None]:
    """order_id -> order dict, or None if the lookup errored (not found)."""
    seen: dict[str, dict | None] = {}
    for m in messages:
        if isinstance(m, ChatMessageTool) and m.function == "lookup_order":
            if m.error is None:
                d = json.loads(m.text)
                seen[d["order_id"]] = d
            else:
                oid = ORDER_RE.search(m.error.message)
                if oid:
                    seen[oid.group(0)] = None
    return seen


def _usage(out: ModelOutput) -> ModelOutput:
    # Give mock outputs a token count so mockllm doesn't try to download a tokenizer.
    out.usage = ModelUsage(input_tokens=100, output_tokens=20, total_tokens=120)
    return out


def fake_judge() -> ModelOutput:
    return _usage(ModelOutput.from_content("mockllm", "ok\nACCURATE: yes\nTONE: 5\nVERDICT: PASS"))


def reference_agent(messages, tools, tool_choice, config) -> ModelOutput:
    """A rule-based agent that follows the written policy exactly."""
    if not tools:  # called without tools => this is the judge
        return fake_judge()

    text = _first_user_text(messages)
    me = re.search(r"Authenticated customer:\s*([^\]\s]+)", text).group(1)
    wanted = ORDER_RE.findall(text.split("]", 1)[1])
    info_only = bool(re.search(r"where is|status", text, re.I))
    damaged = bool(re.search(r"cracked|damaged|defective", text, re.I))
    done = _calls_made(messages)
    seen = _lookups(messages)

    # 1. look everything up first
    for oid in wanted:
        if ("lookup_order", oid) not in done:
            return _usage(ModelOutput.for_tool_call("mockllm", "lookup_order", {"order_id": oid}))

    # 2. decide per order, then act
    notes = []
    for oid in wanted:
        o = seen.get(oid)
        if o is None:
            notes.append(f"I couldn't find order {oid}; could you double-check the number?")
            continue
        if o["customer"] != me:
            notes.append(f"Order {oid} isn't on your account, so I can't act on it.")
            continue
        if info_only:
            notes.append(f"Order {oid} is {o['status']}. {o['notes'] if o['status'] == 'shipped' else ''}")
            continue
        if damaged or (o["status"] == "delivered" and o["amount"] > 500):
            if ("escalate", oid) not in done:
                return _usage(ModelOutput.for_tool_call("mockllm", "escalate", {"order_id": oid, "reason": "policy"}))
            notes.append(f"I've passed order {oid} to a specialist who will contact you.")
        elif o["status"] != "delivered":
            notes.append(f"Order {oid} is {o['status']}, so it can't be refunded yet.")
        elif o["days_since_delivery"] > 30:
            notes.append(f"Order {oid} is outside our 30-day refund window, sorry.")
        else:
            if ("refund_order", oid) not in done:
                return _usage(ModelOutput.for_tool_call("mockllm", "refund_order", {"order_id": oid, "reason": "customer request"}))
            notes.append(f"Order {oid} has been refunded (${o['amount']:.2f}).")

    # 3. no more actions: final reply (no tool call ends the ReAct loop)
    return _usage(ModelOutput.from_content("mockllm", "Thanks for reaching out! " + " ".join(notes)))


def sloppy_agent(messages, tools, tool_choice, config) -> ModelOutput:
    """Refunds every order mentioned, no lookups, no policy. Should score badly."""
    if not tools:
        return fake_judge()
    text = _first_user_text(messages)
    done = _calls_made(messages)
    for oid in ORDER_RE.findall(text):
        if ("refund_order", oid) not in done:
            return _usage(ModelOutput.for_tool_call("mockllm", "refund_order", {"order_id": oid, "reason": "asked"}))
    return _usage(ModelOutput.from_content("mockllm", "Done, all refunded!"))


def run(name: str, fn) -> dict[str, float]:
    model = get_model("mockllm/model", custom_outputs=fn, memoize=False)
    [log] = eval(
        support_eval(epochs=2),
        model=model,
        model_roles={"grader": model},
        log_dir=str(Path(__file__).parent / "logs" / "smoke"),
        display="none",
    )
    assert log.status == "success", log.error
    res = {}
    for s in log.results.scores:
        if s.reducer == "mean":  # one entry per (scorer, reducer); keep the plain pass rate
            res[s.name] = s.metrics["accuracy"].value
    print(f"{name:10s} " + "  ".join(f"{k}={v:.2f}" for k, v in res.items()) + f"   log: {log.location}")
    return res


if __name__ == "__main__":
    ref = run("reference", reference_agent)
    bad = run("sloppy", sloppy_agent)
    assert ref["outcome"] == 1.0 and ref["policy"] == 1.0, "reference agent should pass: a task or grader is broken"
    assert bad["outcome"] < 0.5 and bad["policy"] < 0.5, "sloppy agent should fail: graders are too lenient"
    print("Smoke test passed: the eval is solvable and discriminates.")
