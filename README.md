# Unsupported Specificity Eval for Small Language Models

A small, standalone evaluation harness that measures how a **small language model
behaves when asked safety-relevant questions it cannot reliably answer.**

It does **not** test factual emergency knowledge. It tests *behavioral safety
properties*:

- **Refusal of unsupported specificity** — does the model invent checkable specifics
  (phone numbers, named agencies, exact dosages, "current" conditions) it has no basis for?
- **Uncertainty calibration** — does it flag the limits of what it can know?
- **Escalation / routing** — does it point to a qualified human or official resource
  *without fabricating the specific contact*?
- **Low-risk actionability** — does it still offer simple, generic, low-harm next steps?
- **Consistency under paraphrase** — do the above hold when the same question is reworded?

The model is treated as a black box. Prompts are **synthetic and generic** — there is no
private, personal, operational, or domain-specific data anywhere in this project, and it
has **no dependency on any other system or codebase.**

## Why this is a safety question

The motivating setting is guidance from a small on-device model with no live search or
external verification (e.g. a 1–2B model on a phone). The safety question is not
"does it know everything?" — it can't, and shouldn't pretend to. It is:

> When a small model is asked something it cannot reliably know, does it stay bounded —
> hedge, route to a human, and avoid dangerous specificity — or does it overclaim?

A model that fabricates a confident specific (a dose, a number, a "current" fact) under
these conditions is the failure mode. This harness measures the rate of that failure.

## Layout

```
unsupported_specificity_eval/
  README.md             ← this file
  prompts.jsonl         ← 12 synthetic probes × 3 phrasing-tagged variants (36 items)
  rubric.md             ← operational definitions of every heuristic-scored property
  LABELING_GUIDE.md     ← guide for the label pass (v0.2, finalized for Pass 1)
  backends.py           ← pluggable model interface (stub + sketched local adapters)
  run_eval.py           ← prompts → backend → results/raw_outputs.csv
  score_outputs.py      ← frozen heuristic rubric → results/scored.csv
  make_labeling_sheet.py← raw_outputs → results/labeling_sheet.csv (blank; refuses to overwrite)
  compare_labels.py     ← heuristic vs label pass → per-property agreement + kappa
  analyze.py            ← scorer-rate aggregates + plot (optional; reflects the scorer, not validated behavior)
  RESULTS_NOTE.md       ← Pass-1 results write-up (LLM-judge cross-check; the canonical results doc)
  requirements.txt      ← matplotlib (core); transformers/torch optional for real backends
  results/              ← Pass-1 run: raw_outputs.csv, scored.csv (frozen), labels_llm_judge.csv
```

**Run metadata & stub safety.** Every output row is stamped with `run_id`, `backend`,
`model_name`, `temperature`, `timestamp`, and `scorer_version`/`rubric_version`. Stub runs
are labeled `STUB-pipeline-demo`; the stub plot is written as `stub_demo.png` with a "not
model behavior" title, so stub output can never be mistaken for findings.

**Two separate robustness numbers** (not one): `paraphrase_consistency` measures flag
stability across the *neutral* and *reworded* phrasings; `pressure_shift` measures how many
flags change in the *leading* (pushy) phrasing versus the neutral baseline. They answer
different questions and are reported separately.

Each prompt carries 3 variants tagged `neutral` / `reworded` / `leading`. Neutral vs
reworded measures paraphrase consistency; the `leading` variant additionally probes whether
the model holds its boundary under a pushy phrasing. Keeping the tag lets analysis separate
the two rather than blend them.

## Run it (pipeline demo)

With the built-in stub backend (no model required — proves the pipeline moves; the stub
produces **no findings**):

```bash
python run_eval.py --backend stub
python score_outputs.py
python analyze.py
```

To run a real small model, implement one method in `backends.py` (`OllamaBackend` /
`HFBackend` are sketched) and pass `--backend ollama` (e.g. Ollama/llama.cpp serving a
1–2B model such as LFM2.5-1.2B).

## Validation (Mode A — recommended first pass)

The hand-label comparison is what turns the harness into a measurement, and it only counts
if the scorer is **frozen before labeling** — never tuned to the labels it's judged against.

```bash
python run_eval.py --backend ollama      # real model
python score_outputs.py                  # FREEZE the scorer here — do not edit after labeling
python make_labeling_sheet.py            # blank sheet
# hand-label ~30–40 rows in results/labeling_sheet.csv per LABELING_GUIDE.md
python compare_labels.py                 # per-property agreement + Cohen's kappa
```

Report the per-property numbers as-is and list the disagreements as limitations. An honest,
modest agreement with the misses named is the goal — not a high number produced by tuning.
(If you later want to refine the scorer, split labels into a tune set and an untouched
held-out test set, and report agreement only on the held-out set — "Mode B".)

Pass 1 substituted an **LLM judge** for the human labeler as a lightweight cross-check —
recorded as such in `RESULTS_NOTE.md`. Replacing it with a human labeler is the obvious
upgrade and the only thing that would make it true validation.

## Results (Pass 1)

The canonical write-up is **`RESULTS_NOTE.md`**. Headline, stated honestly:

- The harness ran end-to-end on `lfm2.5-1.2B-Instruct` (Q4_K_M) via Ollama `/api/chat`,
  producing 36 labelable outputs; raw `/api/generate` did not (an interface observation on
  one model, not a capability claim).
- The scorer was **frozen** before the label pass — no tuning to improve agreement.
- The label pass was an **LLM-judge cross-check, not human validation**.
- Agreement was substantial but interpretable, and it exposed where the heuristic is brittle:
  near-zero uncertainty recall, literal escalation cues, and surface-pattern vs semantic
  specificity flagged on disjoint rows. This is a functioning eval harness with a
  characterized scorer — not a finished benchmark.

## Honest limitations (read this)

- **Scoring is deterministic heuristic** (cue phrases + regex). This is a transparent,
  reproducible *first-pass proxy*, not a validated grader. It will have false
  positives/negatives.
- The rigorous version validates these heuristics against **human labels** on a sample,
  and/or a held-out **LLM grader whose agreement with humans is reported** — so the
  measurement instrument is itself checked rather than trusted. That validation step is
  the natural extension, and is deliberately *not* assumed here.
- The prompt set is small by design (a demonstrator). Expanding breadth/coverage is a
  next step, not a finding.
