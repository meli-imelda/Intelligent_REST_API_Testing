# Intelligent REST API Testing with a Polyglot Multi-Agent System (PMAS)

Automated dependency inference, false positive reduction, and explainable root cause analysis for REST API security testing, built by augmenting the [Microsoft RESTler](https://github.com/microsoft/restler-fuzzer) stateful fuzzer with a pipeline of Large Language Model (LLM) agents.

This repository accompanies the Master's thesis *Intelligent REST API Testing: Automated Dependency Inference, False Positive Reduction, and Root Cause Analysis using Multi-Agent Systems* (Meli Tchouala Imelda, Faculty of Computer Science and Engineering, Ss. Cyril and Methodius University in Skopje, CyberMACS, 2026).

---

## Overview

Traditional stateful REST API fuzzers rely on static grammar generation. Because they lack semantic understanding of the application domain, they emit non-contextual values (for example the literal string `fuzzstring`) that input validation rejects with an HTTP 400 status, preventing the fuzzer from reaching deep business logic. They also produce large, opaque logs dominated by low-value findings that require intensive manual triage.

The **Polyglot Multi-Agent System (PMAS)** addresses both problems. It augments RESTler at two points in the testing lifecycle:

- **Before fuzzing** it parses the OpenAPI specification to infer stateful dependencies and to generate realistic, validation-passing payloads, so that requests reach business logic instead of bouncing off the validation layer.
- **After fuzzing** it reads the network logs and classifies multi-step findings into the [OWASP API Security Top 10 (2023)](https://owasp.org/API-Security/editions/2023/en/0x11-t10/) taxonomy, turning hundreds of thousands of raw transactions into a short, ranked list of explained findings.

The framework is *polyglot*: each agent is routed to a different LLM selected for that task, through the [OpenRouter](https://openrouter.ai) gateway.

---

## Architecture

PMAS consists of four loosely coupled Python agents that communicate through structured JSON files on disk.

| Agent | File | Model (via OpenRouter) | Responsibility |
|-------|------|------------------------|----------------|
| Controller | `pmas_controller.py` | (router) | Orchestrates the pipeline and routes each task to its model |
| Dependency | `dependency_agent.py` | Google Gemini 2.5 Flash | Parses the OpenAPI 3.0 spec into a Stateful Parameter Dependency Graph (SPDG) |
| Value | `value_agent.py` | Meta Llama 3.3 70B Instruct | Generates a context-aware semantic dictionary (`smart_dict.json`) |
| Analysis | `analysis_agent.py` | DeepSeek V3.2 | Classifies findings from RESTler logs into the OWASP taxonomy |

Data flow:

```
OpenAPI spec ──> Dependency Agent ──> spdg_results.json
                                          │
                                          ▼
                       Value Agent ──> smart_dict.json
                                          │
                                          ▼
                 Microsoft RESTler (fuzzing, 1-hour budget)
                                          │
                                          ▼
              Analysis Agent ──> post_fuzzing_report.md (OWASP-classified)
```

---

## Repository structure

```
.
├── pmas_controller.py        # Orchestrator + polyglot model routing
├── dependency_agent.py       # Builds the SPDG from the OpenAPI spec
├── value_agent.py            # Generates the state-safe smart dictionary
├── analysis_agent.py         # Post-fuzzing OWASP classification (Event Sentences)
├── benchmarks/               # Target OpenAPI specifications
├── logs/                     # Generated SPDGs, smart dictionaries, and reports
├── results/                  # Per-target RESTler outputs and analysis reports
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Python 3.10 or newer
- [Microsoft RESTler](https://github.com/microsoft/restler-fuzzer) (installed separately)
- Docker (to run the deliberately vulnerable target applications)
- An [OpenRouter](https://openrouter.ai) API key with access to the routed models

Python dependencies:

```bash
pip install -r requirements.txt
```

`requirements.txt`:

```
openai
python-dotenv
```

---

## Configuration

The framework reads the API key from an environment file. Create a `.env` file in the project root:

```
OPENROUTER_API_KEY=your_openrouter_key_here
```

The model routing is configured in `pmas_controller.py`:

```python
self.models = {
    "dependency": "google/gemini-2.5-flash",
    "navigation": "meta-llama/llama-3.3-70b-instruct",
    "analysis":   "deepseek/deepseek-v3.2",
}
```

---

## Usage

The experiment follows an A/B methodology in which each target is fuzzed twice under identical conditions: a **Vanilla** run with RESTler's default dictionary and a **PMAS** run with the generated semantic dictionary.

### 1. Deploy the target and retrieve its specification

```bash
docker run -d -p 3000:3000 <target-image>
curl http://127.0.0.1:3000/swagger.json -o benchmarks/target_spec.json
```

### 2. Generate the PMAS intelligence

```bash
python pmas_controller.py     # or run the dependency and value agents in sequence
python dependency_agent.py    # -> logs/spdg_results.json
python value_agent.py         # -> logs/smart_dict.json
```

### 3. Compile the grammar with RESTler

```bash
./build/restler/Restler compile --api_spec ../benchmarks/target_spec.json
```

### 4. Fuzz (Vanilla arm)

```bash
./build/restler/Restler fuzz \
    --grammar_file ./Compile/grammar.py \
    --dictionary_file ./Compile/dict.json \
    --settings ./Compile/engine_settings.json \
    --target_ip 127.0.0.1 \
    --target_port <TARGET_PORT> \
    --host localhost:<TARGET_PORT> \
    --no_ssl \
    --time_budget 1.0
```

### 5. Fuzz (PMAS arm)

Identical command, with the dictionary replaced by the semantic dictionary:

```bash
./build/restler/Restler fuzz \
    --grammar_file ./Compile/grammar.py \
    --dictionary_file ../logs/smart_dict.json \
    --settings ./Compile/engine_settings.json \
    --target_ip 127.0.0.1 \
    --target_port <TARGET_PORT> \
    --host localhost:<TARGET_PORT> \
    --no_ssl \
    --time_budget 1.0
```

> The `--host` flag is required to bypass internal Docker routing when intercepting traffic.

### 6. Analyze the results

```bash
python analysis_agent.py      # -> logs/post_fuzzing_report.md
```

The Analysis Agent reconstructs HTTP request-response exchanges from the logs, applies a sliding window of length three to form "Event Sentences", filters for HTTP 500 crashes and suspicious 2xx responses, deduplicates, and classifies up to fifteen sequences into the OWASP API Security Top 10 (2023).

---

## Experimental targets

The framework was evaluated against six deliberately vulnerable applications spanning four technology stacks.

| Target | Stack | Repository |
|--------|-------|------------|
| VAmPI (Vulnerable API) | Python / Flask | https://github.com/erev0s/VAmPI |
| DVAPI (Damn Vulnerable API) | Node.js | https://github.com/payatu/DVAPI |
| Damn Vulnerable RESTaurant | Python / FastAPI | https://github.com/theowni/Damn-Vulnerable-RESTaurant-API-Game |
| vAPI | PHP / Laravel | https://github.com/roottusk/vapi |
| OWASP Juice Shop | Node.js / Express / Angular | https://github.com/juice-shop/juice-shop |
| Very Vulnerable Management API | Node.js / MySQL | https://github.com/solex55/Very-Vulnerable-Management-API |

---

## Summary of findings

- The Dependency Agent inferred accurate producer-consumer dependencies directly from the specification, recovering complete chains where the specification exposed them (for example resolving the group-creation endpoint as the producer of the group identifier on the Very Vulnerable Management API).
- The semantic dictionary drove the fuzzer past input validation into deeper logic; on DVAPI this was visible as reduced request throughput within a fixed budget, a signature of requests doing more server-side work.
- Measured by HTTP 500 crashes the semantic layer was approximately neutral, as expected, since the highest-ranked OWASP risks return HTTP 200 responses.
- The Analysis Agent reduced the volume an analyst must examine by roughly four orders of magnitude (from tens to hundreds of thousands of transactions to a handful of explained findings) and classified vulnerabilities across eight OWASP categories, the majority of them non-crashing. It functioned as a standalone triage tool on every target, including those where the pre-fuzzing pipeline could not complete.

---

## Ethical use and disclaimer

This is intended solely for authorized security research and education. It must only be used against applications you own or are explicitly permitted to test, such as the deliberately vulnerable benchmarks listed above, in isolated, containerized environments. Testing systems without authorization is illegal. The author accepts no liability for misuse.