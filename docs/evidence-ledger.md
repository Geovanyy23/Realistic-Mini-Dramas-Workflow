# Evidence ledger

Labels used throughout: `official documented capability` · `historical observed UI` · `community anecdote` · `proposed hypothesis` · `actual measured result`.

## Actual measured results (2026-10-23, live VideoExpress runs)
- Three complete pilots generated and exported through the editor UI: v1 16:9 8×7 s, v2 9:16 9×5 s, v3 9:16 9×5 s 3D-cartoon (Creative mode). See `docs/run-report.md`.
- Account concurrency cap: 5 AI videos in parallel (refusal message observed, nothing created, retry succeeded).
- Form controls, durations, ratios, export path and library behaviour: `docs/capabilities.md`.

## Historical observed UI
- Authenticated editor observation dated 2026-07-31 (control names) — superseded by the live audit above.

## Proposed hypotheses (not yet measured)
- One-speaker-per-close-up improves dialogue attribution; locked camera reduces identity drift; verbatim quoted lines reduce added speech. These are the design rules the pack enforces, pending a formal rubric pass over the rendered clips.

## Private
Source-video analysis, transcripts, frames and run IDs stay in the owner's private research package and in `private/` (git-ignored); only original prose and prompts are in this package.
