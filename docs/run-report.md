# Live test run report — 2026-10-23

All runs were performed through the VideoExpress editor UI (app.videoexpress.ai, "3.5" editor) in Claude's built-in browser with parallel operator agents, one dedicated tab each. No API, no private endpoints.

| Run | Pack | Format | Shots | Look | Operators | Brief → export |
|---|---|---|---|---|---|---|
| v1 | `examples/farmer-zombie` | 16:9, 8 × 7 s ≈ 56 s | 8 | Photorealistic (Cinematic) | 3 | ≈ 35 min (incl. a 20‑min pause for the gallery decision) |
| v2 | `examples/farmer-zombie-v2` | 9:16, 9 × 5 s = 45 s | 9 | Photorealistic (Cinematic) | 3 | ≈ 20 min |
| v3 | `examples/farmer-zombie-v3-3d` | 9:16, 9 × 5 s = 45 s | 9 | Image Type 3D + Creative mode | 8 | ≈ 25 min (3 shots delayed by the 5‑parallel cap) |

Story: **Hold the Line** — an original mini drama about a farmer protecting his wife and adult daughter through one night of an outbreak. Beats: dinner calm → radio warning → boarding the door → window breach → fight → engine won't start → headlights through the horde → the barn burns → dawn, "We held."

## What worked
- **Per-shot recipe** (see `skills/realistic-mini-dramas/references/browser.md`): Create Video From Prompt → ratio → Image Prompt → Video and Audio Prompt → Image Type → (Creative mode) → Advanced Mode → Manual Video Length → uncheck public gallery → Create Image → Create Video once.
- **Parallel operators**: independent tabs are safe; the account refuses the 6th concurrent job with a visible message and creates nothing, so operators retry after ~60–90 s.
- **Assembly**: Media Library → My AI Videos (cards are titled by the video prompt, so prefix each prompt with a unique shot cue), drag to track 1 in story order, Auto Align, Save, Export (High / FullHD / mp4), My Videos → download.
- First frames matched the briefs on every shot except one (v1 S080 needed one image retry: extra person in frame).

## What to watch
- "Share this in the public gallery" is **on by default**. Uncheck it on every shot.
- Image enhancer / Creative mode rewrite the image prompt text; the video prompt is left alone unless the Advanced "enhance video prompt" box is on.
- The dialog remembers everything between shots — overwrite both prompts and re-verify checkboxes each time.
- Library thumbnails render portrait-cropped even for landscape clips; trust the clip dimensions, not the thumbnail.
- No cost or credit figure is shown anywhere in the UI; no model name is shown on the form.

## Not yet done
- Rubric QA on motion/lip-sync (first frames reviewed only).
- GitHub push and community publication — both need explicit owner authorization.
