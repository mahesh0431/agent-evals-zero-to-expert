# Tool-call eval: four checks and a paired A/B

Companion to [Module 06: Tool use, RAG and conversation](../../../modules/06-tool-use-and-conversation.html)
and [Module 24: Evaluating tools and MCP servers](../../../modules/24-tools-and-mcp-evals.html).

```bash
python tool_call_eval.py
```

Standard library only. No API key. Runs in well under a second.

## What it teaches

A deterministic mock agent answers 20 tasks (flight search, weather, currency
conversion, customer lookup, order cancellation, booking) by emitting tool calls.
It understands every request perfectly; its only mistakes come from what the tool
descriptions say. That isolates the one thing we change between two runs: the
wording of the tool descriptions.

* **Grade tool calls on separate axes.** Each task is scored on *selection* (right
  tools, nothing missing, nothing extra), *schema* (types, patterns, enums),
  *values* (the expected arguments exactly) and *order* (look up before you cancel).
  A task passes only if all four pass. The breakdown tells you what to fix.
* **Report an interval, not a point.** Pass rates come with a Wilson 95% interval.
  With 20 tasks it is wide (about plus or minus 20 points).
* **Compare variants on the same tasks.** The 2x2 table, the exact McNemar test and a
  paired bootstrap interval use the pairing, which is far more sensitive than
  comparing two independent intervals.
* **Look at regressions, not just the net gain.** Variant B fixes 12 tasks and breaks 2:
  the sentence "flight_id comes from search_flights" makes the agent search even
  when the user already gave a flight id.

## Try this

The self-checks at the end of the script assert this exact setup, so some
experiments will trip them on purpose. Read the report above the assertion.

* Delete "Always call get_order first" from `DESC_B["cancel_order"]` and rerun.
  Which column changes?
* Fix the regression: rewrite `DESC_B["book_flight"]` without the phrase "comes from
  search_flights" (for example: "Book a flight by flight_id. If the user already gave
  one, book it directly.") and check the McNemar p-value again.
* Drop to 8 tasks (`TASKS[:8]`): the same improvement is no longer significant.
