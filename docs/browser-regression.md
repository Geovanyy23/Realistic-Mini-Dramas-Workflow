# Browser regression investigation — 2026-10-23 (Asia/Dhaka)

## Reported failure

The user supplied a ChatGPT message saying its browser inspection tool failed to start, followed by a stop because the model could not be verified. The original ChatGPT runtime and tool logs were not available; its startup failure was not reproduced and its underlying cause is unknown.

## Direct observations in the user-selected Chrome session

- Browser control connected successfully. VideoExpress initially redirected to login; the user signed in.
- Create with AI → Create Video From Prompt opened successfully. A 3.5 badge is visible; no underlying vendor-model selector/name or per-generation price is displayed in this form.
- Image Prompt, Video and Audio Prompt, Landscape 16:9 / Vertical 9:16, image styles, consistent-character controls, and audio controls are readable.
- Advanced Mode exposes video prompt enhancement, Video Only (No Sound), and a manual-duration slider marked 3–10 seconds.
- Public-gallery sharing was checked. It was unchecked and verified OFF. Reopening the dialog reset it to ON, requiring another explicit uncheck.
- An exact-name Advanced Mode checkbox action timed out after the control had already become checked and acquired a decorative prefix. Re-reading state avoided undoing the successful change.
- Media Library → My Media → My AI Videos opened; the folder was empty before the test.
- The user authorized generation testing after being told no price was displayed. One image-generation click for an original Eli close-up opened a six-step Terms of Service dialog. No image output or job receipt was verified at that point; the user was asked to handle the agreement.

## Confirmed prompt defects

The published prompt required a visible model name even though the live form exposes only the workflow/version badge. It also provided no browser-startup recovery branch and allowed the audit to block writing the draft contract. These are distinct from the unobserved cause of the original ChatGPT tool startup failure.

## Fix scope

The revised prompt drafts first, uses the actual connected browser, distinguishes connection/login/model metadata, and uses the live workflow by default without claiming a vendor model identity. Explicit exact-model requests remain strict. Missing prices are not treated as zero and require bounded operation approval. The CLI adds an explicit live-default selection policy while preserving strict behavior for legacy plans.

## Verification status

32 local tests pass, including five model-policy regression tests. Live preflight succeeded. Image/video generation and playback verification are pending the account prerequisite; this report is not an end-to-end success claim.
