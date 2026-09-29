# Agent Evals: Zero to Expert

A free, visual course on evaluating AI agents across every modality: tool calls, code, browsers and desktops, voice, images and video, and multi-agent systems. It starts from "what is an eval?" and ends with how frontier labs run dangerous-capability evaluations.

**Read it online:** https://mahesh0431.github.io/agent-evals-zero-to-expert/

## What's inside

- **20 modules in 4 parts**, each built around inline diagrams (over 200 in total), with runnable code, worked examples, a self-check quiz and cited sources.
- **Interactive widgets**: score noise, confidence intervals, paired A/B comparisons, pass@k vs pass^k, compounding errors, judge-error correction, word error rate and Arena ratings. All of them are collected in the [Eval Playground](https://mahesh0431.github.io/agent-evals-zero-to-expert/playground.html).
- **A runnable capstone** in [`code/capstone`](code/capstone): an [Inspect](https://inspect.aisi.org.uk/) eval of a tool-using support agent, with outcome, policy and LLM-judge scorers, pass^k over epochs, analysis scripts and a CI gate.

| Part | Modules |
|---|---|
| I · Foundations | 01 What an eval is · 02 Anatomy of an eval · 03 Graders · 04 Metrics and statistics |
| II · Agent evals, every modality | 05 Why agents are different · 06 Tool use, RAG and conversation · 07 Coding agents · 08 Web and computer use · 09 Voice agents · 10 Vision, image and video · 11 Multi-agent and long-horizon |
| III · Practice | 12 Error analysis · 13 LLM-as-a-judge · 14 The tools landscape · 15 Evals in production and CI |
| IV · Expert | 16 How the labs do evals · 17 Safety and dangerous-capability evals · 18 Benchmark pitfalls · 19 Capstone · 20 Expert drill, glossary and map |

## Run locally

It is a static site with no build step:

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Accuracy

Facts about tools, benchmarks and lab practices were checked against primary sources (papers, official docs, system cards, lab blogs) in September 2026 and are cited at the end of each module. The field moves fast; when a number matters, follow the link and check the current value. Corrections are welcome as issues or pull requests.

## License

Course text and diagrams: CC BY 4.0. Code: MIT. three.js (vendored in `assets/vendor`) is MIT-licensed by its authors.
