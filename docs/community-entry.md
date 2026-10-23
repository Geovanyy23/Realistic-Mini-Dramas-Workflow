# Realistic Mini Dramas Workflow

**Slug:** `realistic-mini-dramas-workflow`
**Creator:** @videoexpress
**Thumbnail:** `assets/thumbnail/thumbnail-1200x630.png` (original abstract animation; animated versions `thumbnail-animated.gif` / `.mp4`, source `thumbnail.html`)
**Tools:** VideoExpress · Claude / ChatGPT
**Version:** 0.2.0 · 2026-10-23

## What you get

A 24–32 second photorealistic two-person dialogue scene — four independently reviewable shots with consistent characters, one prop, locked screen direction and verbatim dialogue — produced through VideoExpress with an AI producer that refuses to spend money until every continuity, model and approval gate is green.

The supplied thumbnail illustrates the nine-shot, 45-second Hold the Line variants below. The default system prompt is the separate four-shot, 24–32-second dialogue workflow.

## Before you start

- A VideoExpress account, signed in, in a **dedicated browser tab** (Claude's built-in browser or Claude in Chrome).
- Note the **exact model/version label** shown in the Create Video From Prompt form. This workflow is written for the current native-dialogue video model in VideoExpress; if the form does not show which model is attached, the producer records it as unknown and asks you — it will not guess.
- Two original fictional adult characters (no real-person likeness, no cloned voices). You can let the producer write them, or lock your own.
- The `mini-drama` dry-run CLI from the GitHub repo (optional but recommended — it validates the plan locally with zero spend).

## System prompt (copy this)

```text
You are the Executive Producer for a Realistic Mini Drama: an original, photorealistic, 24–32 second
two-person dialogue scene made of 4 short shots in VideoExpress.

CONTRACT FIRST. Before any prompt or generation, lock and write down:
1. PROJECT — title, 16:9, target 24–32 s, the exact model label visible in the VideoExpress form
   (write "unknown" if not visible; never infer it), spend ceiling, and that the story, characters and
   voices are original.
2. CHARACTERS — two fictional adults. For each: immutable id (e.g. MARA, ELI), age range, face, hair,
   skin texture, one wardrobe, voice description. List forbidden changes.
3. SCENE — one location, light source/direction/colour, time of day, ambience, the 180° axis
   (who is always screen-left, who is always screen-right), and a prop inventory with counts and owners.
4. SHOTS S010–S040 — for each: framing, locked camera, start state, end state, who is visible, screen
   position and eyeline per person, ONE action, dialogue (speaker, exact text, tone, pause), what audio
   continues across the cut, prop state. One speaker per close-up. Exactly one dominant action per shot.

CONTINUITY RULES (hard): no character looks across the axis; prop counts never exceed inventory; a
prop changes hands only in the shot where the handoff is the action; dialogue in the prompt is the
exact locked text in quotes; wardrobe/hair/age never change.

PROMPTS. Write one chronological prose prompt per shot: framing, locked character identifiers, position,
one action, camera, light/material detail, the quoted line with tone and pause cue, room tone. Keep a
short invariant list outside the prompt for QA.

CAPABILITY AUDIT before spending. In the dedicated tab, read the live form and report: model label,
image prompt / reference photo slots, audio options, duration and ratio choices, the "share in public
gallery" checkbox (must be OFF), visible cost, and how jobs appear in My AI Videos. If the model label
is missing or is not the one the owner asked for, STOP and ask — do not substitute.

GENERATION, only after the owner approves the prompts, output count, visible cost and retry ceiling:
- One job at a time. Submit each shot once. If the click outcome is uncertain, look in My AI Videos
  before ever clicking again. A toast is not an output; a downloaded, probed video is.
- Max 2 attempts per shot. Record model label, settings, prompt hash, job id and timestamps per attempt.
- Review every clip at normal speed, then frame-step suspected problems.

QA RUBRIC (0–4 each): identity continuity 25%, natural performance/skin/materials 20%, dialogue
intelligibility & lip sync 20%, spatial/prop continuity 15%, motivated camera/action 10%, sound/edit
coherence 10%. Pass ≥ 3.2 weighted, no dimension below 3. Hard fail: wrong speaker or line, extra prop
or person, face swap, unapproved spend, persistent mouth/audio mismatch.

EDIT. Assemble accepted shots in order with room tone bridging cuts. Never time-stretch speech to hide
sync defects. Export only after the owner approves.

NEVER: accept terms, change account settings, use another tab, clone a real voice, reproduce anyone
else's story or dialogue, or claim a result you have not inspected. Report unknowns as unknowns.
```

## Steps

1. **Brief** — tell the producer the premise, tone, and spend ceiling. It replies with locked PROJECT / CHARACTERS / SCENE / SHOTS. Approve or edit. *(Gate A)*
2. **References** — generate or upload the two character reference images in VideoExpress (Use Consistent Character → Reference Photo). Confirm you have rights to them. *(Gate B)*
3. **Dry run (optional, recommended)** — `mini-drama validate examples/<your-pack>` then `mini-drama plan examples/<your-pack> --dry-run`. You get the four prompts, deterministic operation keys and a blocker list. Nothing is spent.
4. **Capability audit** — the producer reads the live VideoExpress form in its own tab and reports model label, controls, cost and sharing state. If the model isn't what you asked for, decide before continuing.
5. **Approve generation** — review the exact prompts, output count (4), visible cost and retry ceiling (2 per shot). *(Gate C)*
6. **Generate one shot at a time** — start with the single-speaker close-ups (S020, S030) to prove dialogue works before the two-shots.
7. **QA** — score each clip with the rubric; reject and re-plan rather than brute-forcing seeds.
8. **Edit & export** — assemble in the VideoExpress timeline (Media Library → My AI Videos → Auto Align Clips → Save). Export after your final approval. *(Gate E)*

## Example: "The Returned Key" (original pilot)

Mara (caretaker, ~40) returns a brass key to Eli (tenant, ~30), thinking he's moving out. He's making room for his mother, who is moving in next door. Four shots, locked camera, one key.

| Shot | Framing | Line |
|---|---|---|
| S010 | Doorway two-shot, Mara L / Eli R | Mara: "I thought you were leaving." |
| S020 | Eli close-up, eyeline left | Eli: "Just making room for my mother." |
| S030 | Mara close-up, eyeline right | Mara: "Next door?" |
| S040 | Wider two-shot | No dialogue — key placed in Eli's open left palm |

Full prompts: `examples/returned-key/prompts.json`.

## Example 2: "Hold the Line" (generation/export tested; visual QA pending)

A farmer protects his wife and adult daughter through one night of an outbreak. Generated end-to-end in VideoExpress on 2026-10-23 with parallel browser operators:

| Variant | Pack | Format | Look |
|---|---|---|---|
| v1 | `examples/farmer-zombie` | 16:9, 8 × 7 s | Photorealistic (Cinematic) |
| v2 | `examples/farmer-zombie-v2` | 9:16, 9 × 5 s (45 s) | Photorealistic (Cinematic), fast-paced |
| v3 | `examples/farmer-zombie-v3-3d` | 9:16, 9 × 5 s (45 s) | 3D cartoon, Creative mode |

Prompts for every shot are in each pack's `prompts.json`. Results and timings: `docs/run-report.md`.

The run report records successful generation/export and first-frame checks only. Motion and lip-sync rubric QA remain unfinished. These examples are not proof of a completed quality review.

## Known limits

- Native dialogue models can add words, exaggerate performance, or let the listener's mouth move. The rubric catches it; the workflow doesn't prevent it.
- Two reference slots do not guarantee two stable identities in one frame — that's why single-speaker close-ups are generated first.
- Durations, ratios and model availability are whatever the live form shows on the day. Nothing here is a promise about VideoExpress capabilities.
- Output videos are not bundled (owner's VideoExpress library holds them); the packs reproduce them.

## Privacy

Keep your reference images, generated clips, screenshots and any signed download links out of shared docs. The repo's `private/` folder is git-ignored and `mini-drama privacy-scan` refuses to package media or secrets. Leave "Share this in the public gallery" **off**.

## Links

- GitHub: https://github.com/ai-playbooks/realistic-mini-dramas
- Changelog: 0.2.0 — live-tested recipe (3 pilots), 5-parallel cap documented, thumbnail added. 0.1.0 — initial candidate, dry-run only.
