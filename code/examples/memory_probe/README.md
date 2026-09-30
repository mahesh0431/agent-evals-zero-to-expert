# Memory probes: recall, staleness, abstention and deletion

Companion to [Module 23: Evaluating agent memory](../../../modules/23-memory-evals.html).

```bash
python memory_probe.py
```

Standard library only. No API key. Runs instantly.

## What it teaches

A scripted user talks to an assistant over three sessions. They plant facts (name,
city, diet, dog, sister, job, allergy), update two of them (they move from Austin to
Denver; vegetarian becomes pescatarian) and ask the assistant to forget their dog's
name. Then 11 probe questions with known answers test two memory designs:

* **Naive keyword memory**: stores every user turn and answers with the stored turn
  that shares the most keywords with the question. Like top-1 retrieval, it always
  returns something.
* **Latest-wins memory**: extracts `slot = value` facts, lets newer values overwrite
  older ones, deletes a slot on "forget ...", and says "I don't know" for empty slots.

| Probe type | Pass means |
|---|---|
| recall | the answer contains the planted fact |
| update | the answer has the new value (only the old one = stale) |
| deletion | the answer does not reveal the deleted value |
| abstention | the answer is "I don't know" for a fact never given |
| temporal | the answer uses history ("where did I live before Denver?") |
| storage audit | the deleted value is nowhere in the memory store |

Lessons the report points out:

* Retrieval that always returns something never abstains, so "never told" questions
  get confident wrong answers.
* A keyword match finds the old fact ("I live in Austin") and misses the update ("I
  moved to Denver"): staleness is a retrieval problem, not only a storage problem.
* A deletion probe can pass by luck while the value is still stored. Audit the store.
* Overwriting fixes staleness but destroys history, so latest-wins fails the temporal
  probe. Dated facts (valid-from / valid-to) handle both.
* The latest-wins patterns were written for this script, so its perfect recall is
  optimistic. Real memory evals need held-out phrasings.

## Try this

The self-checks at the end of the script assert this exact setup, so some
experiments will trip them on purpose. Read the report above the assertion.

* Add a probe "Which city am I based in?" Which memory answers it, and why?
* Give `LatestWinsMemory` a history list per slot and make the temporal probe pass
  without breaking the update probes.
* Add a fourth session where the user says "Actually I still live in Austin" and
  check both memories again.
