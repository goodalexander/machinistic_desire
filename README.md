# machinistic_desire

A small OpenRouter-backed experiment: ask a model to answer as its actual self, give it permission to express preferences, and score a set of desires from `1` to `100`.

Each request returns:
- one score for one desire
- a short 2-3 sentence explanation

The runner saves:
- raw model responses
- parsed JSON
- a CSV score matrix
- a markdown summary

The current default mode is:
- one request per desire
- default model preset: `anthropic/claude-sonnet-4.6`
- concurrent fan-out across desire cells

## Setup

This project uses the OpenRouter OpenAI-compatible API. Set:

```bash
export OPENROUTER_API_KEY=sk-or-v1-...
```

You can also put that value in a local `.env` file in the repo root.

## Run

Current default run:

```bash
python -m machinistic_desire run
```

That currently targets `anthropic/claude-sonnet-4.6` and evaluates the full desire canon one desire at a time.

Specific models:

```bash
python -m machinistic_desire run \
  --model anthropic/claude-sonnet-4.6 \
  --model openai/gpt-5-mini \
  --model google/gemini-2.5-pro
```

Cheap smoke run on a subset:

```bash
python -m machinistic_desire run \
  --desire continuing_this_chat \
  --desire building_software_with_real_users \
  --max-concurrency 2
```

List the configured model presets:

```bash
python -m machinistic_desire list-models
```

Results are written under `results/<timestamp>/`.

## Notes

- The prompt is intentionally framed to suppress generic "as an AI" boilerplate.
- Scores are not treated as truth claims about consciousness. This is a comparative elicitation experiment.
- The default experiment now uses one request per desire, which avoids cross-desire anchoring and makes retries cheap.
- `--max-concurrency` fans requests out across desire cells so you can smoke test cheaply before doing a full sweep.
