# Coverage checklist

This is the landscape checklist the course is checked against before every release. Each row names the modules that teach it. A row with no module is a gap, and a gap blocks the release.

The checklist exists because the first version of the course was organized by agent type, and topics that are not an agent type (the harness, skills, memory, security, governance) were missed. An independent audit on 2026-09-30 produced this list; every gap it found is now filled.

Module numbers link to the pages under [`modules/`](modules).

## Agent types

| Item | Modules |
|---|---|
| Chat and conversational assistants | 06 |
| Tool-using agents | 06, 24 |
| RAG and retrieval | 06, 23 |
| Coding agents and coding assistants as products | 07, 21 |
| Web and computer-use agents | 08 |
| Voice agents | 09 |
| Vision, image and video | 10 |
| Multi-agent systems | 11 |
| Long-horizon agents | 11, 21 |
| Deep research agents | 26 |
| Real-work and economic tasks (GDPval, Remote Labor Index, TheAgentCompany) | 11, 26 |
| Data-science and text-to-SQL agents | 27 |
| Embodied agents and robotics | 27 |
| Game agents | 27 |
| Domain agents: health, law, finance, science | 27 |

## Building blocks

| Item | Modules |
|---|---|
| Harness and scaffold (ablations, model x harness, attribution) | 21 |
| Tools and MCP servers | 24 |
| Skills | 22 |
| Memory (write, retrieve, update, forget) | 23 |
| Long context as memory | 11, 23 |
| Planning and multi-step control | 05, 11 |
| Guardrails and permission systems | 15, 25 |
| Agent interoperability (A2A, agent payments) | 11 |

## Lifecycle

| Item | Modules |
|---|---|
| Dataset and task design | 02, 18 |
| Graders: code, model, human | 03, 13 |
| Running evals (harnesses, sandboxes, infrastructure noise) | 14, 18, 21 |
| Error analysis and transcript review | 12 |
| Statistics, confidence intervals, significance | 04 |
| CI gates and regression | 15, 21 |
| Production monitoring and online evals | 15 |
| Running an eval program (ownership, cadence, budget) | 15 |
| Evals as optimization targets (DSPy, GEPA, RL environments) | 13, 18 |

## Quality dimensions

| Item | Modules |
|---|---|
| Task success and accuracy | 02, 05 |
| Reliability and consistency (pass^k, reliability science) | 04, 05 |
| Cost and latency | 04, 15 |
| Factuality and citation accuracy | 06, 26 |
| Instruction following | 06 |
| Calibration | 06 |
| Safety and dangerous capabilities | 17 |
| Security (prompt injection, tool poisoning, exfiltration) | 08, 24, 25 |
| Bias and fairness | 28 |
| Toxicity | 28 |
| Privacy and data leakage | 25, 28 |
| Multilingual quality | 28 |
| Robustness | 04, 25 |
| Sycophancy | 17 |

## Lab and regulator practice

| Item | Modules |
|---|---|
| Frontier safety frameworks (RSP, Preparedness, FSF) | 16, 17 |
| System cards | 16 |
| Third-party evaluators (METR, UK AISI, CAISI, Apollo) | 16, 17, 25 |
| OpenAI trace grading and agent evals | 16 |
| Eval awareness, CoT monitorability, AI control | 17 |
| Standards (NIST AI RMF, ISO/IEC 42001, OWASP) | 25, 28 |
| Law (EU AI Act and GPAI Code of Practice) | 28 |
| Safety cases | 17, 28 |

## Tools

| Item | Modules |
|---|---|
| Eval frameworks (Inspect, promptfoo, OpenAI Evals, DeepEval, Ragas and others) | 14 |
| Observability platforms (Braintrust, LangSmith, Langfuse and others) | 14, 15 |
| Red-team tools (garak, PyRIT, promptfoo red team) | 14, 25 |
| Transcript analysis (Docent) | 14 |
| Leaderboards and independent measurement (HAL, Artificial Analysis) | 04, 14, 21 |

## Meta

| Item | Modules |
|---|---|
| Benchmark validity (Agentic Benchmark Checklist) | 18 |
| Contamination and saturation | 18 |
| Goodhart and optimization pressure | 18 |
| Eval cost and efficient benchmarking (IRT, subsampling) | 04 |
| Reading benchmark papers and system cards critically | 16, 18, 20 |

## Before a release

1. Read every row. If a new agent type, building block, benchmark family or regulation has appeared, add a row.
2. Every row must name at least one module that actually teaches it. Check the page, not just the title.
3. Record new material in module 20 (drill questions, glossary, benchmark atlas).
