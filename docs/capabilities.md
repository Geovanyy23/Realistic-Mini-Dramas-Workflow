# VideoExpress capability report

**Status: `audited` (live, 2026-10-23 10:56–10:58 ET, authenticated editor at `https://app.videoexpress.ai/`, dedicated built-in-browser tab).** Label: *historical observed UI → now live-observed*. No generation had been submitted at audit time.

## Create with AI menu (live)
Create Video From Prompt (Image to Video · Lipsync HD · Narrate · Consistent Character) with a **"3.5" badge** · Text To Video (Lipsync HD, "3.5") · First Frame, Last Frame · Smart Edit · Stylize Character · Image To Video (Old Algorithm) · Lipsync Video (Old Algorithm, up to 5 min) · Outpainting · Change Aspect Ratio · AI Sound Maker.

## Create Video From Prompt form (live)
| Control | Observed |
|---|---|
| Aspect ratio | Landscape 16:9 / Vertical 9:16 buttons inside the dialog (dialog defaulted to Vertical even though editor was Landscape) |
| Image Prompt | textarea (first frame) |
| Video and Audio Prompt | textarea; **"New — Multi-Shot"** label beside it |
| Image Type | select: Human (default) / 2D / 3D / Photorealistic (Cinematic) / Other |
| Use Creative mode | checkbox, off |
| Automatically enhance my image prompt | checkbox, **on by default** |
| Use Consistent Character + Use from Library | checkbox off; library picker |
| Lipsync HD Video / Narration Video (Choose my Audio) | checkboxes, off |
| **Share this in the public gallery** | checkbox, **ON by default** — must be unchecked per privacy rule (owner declined the uncheck click at 10:56; left as-is pending owner decision) |
| Advanced Mode | reveals: Automatically enhance my video prompt (off) · Video Only (No Sound) (off) · Manual Video Length, sec (slider 3–10, default 5) |
| Buttons | Enhance Prompt · Create Image · + Consistent Character · Create Video |

## Unknowns that remain
- **Model identity: no model name is shown on the form.** Only the "3.5" badge in the menu. The requested label "Fable 5.1 for Claude" does not appear anywhere → `project.model_label.observed = "3.5 (menu badge; vendor model name not shown)"`, `identity_verified = false`. The underlying vendor model is not evidenced by the UI.
- Cost per generation: not shown on the form at audit time.
- Max duration per clip: 10 s via slider. A 60 s piece therefore needs ≥ 6 clips, or the Multi-Shot mode whose output length is unknown.
- Queue/job identity and My AI Videos binding: to be recorded at first submission.

## Live findings from generation runs (2026-10-23)
- **Queue cap: "You can generate up to 5 AI videos in parallel"** — 6th concurrent Create Video is refused with that message and creates nothing (verified: no Video id). Retry after ~60–90 s succeeds. This is the authoritative concurrency limit for one account; the historical five-slot rule is confirmed.
- Receipt: toast + "Video: <uuid>" text; library card titled by the video prompt; progress ring % on the card; completion toast.
- Image outputs: 1920×1088 (landscape) / 1088×1920 (vertical). Manual Video Length 3–10 s; toggling the checkbox resets the slider to 10.
- "Use Creative mode" and "Automatically enhance my image prompt" both rewrite the Image Prompt text in the box; the video prompt enhancer is separate (Advanced Mode) and off by default.
- Dialog retains all previous values and generated images (carousel) between opens; Close button unreliable, top-right X works.
- Export: Export Video → High / FullHD / mp4 → server-side queue ("number N in the queue") → My Videos list with /download/output/<id>; files hosted 40 days.
