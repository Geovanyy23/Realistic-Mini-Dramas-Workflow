# QA review flow

Two reviewers score independently; owner resolves disagreement. Review at normal speed first, then frame-step flagged moments. Automated ASR/face metrics are advisory only.

| Dimension | Weight |
|---|---|
| Identity continuity (face, hair, wardrobe vs locked references) | 25% |
| Natural performance, skin, materials | 20% |
| Dialogue intelligibility & lip sync (exact words, right speaker, no added speech) | 20% |
| Spatial / prop continuity (axis, eyelines, one key, box) | 15% |
| Motivated camera / single clear action | 10% |
| Sound / edit coherence (room tone, no duplicate audio) | 10% |

Score each 0–4. **Pass:** weighted ≥ 3.2 and no dimension < 3 and no hard fail.
**Hard fail:** wrong speaker or line · extra key/person · face swap · unsafe rights · missing provenance · unapproved spend · persistent mouth/audio mismatch · broken hand contact at the key transfer (S040) · HTML/empty/silent file where dialogue is required.

Record per take: run id, shot id, operation key, provider job id, observed model label and settings, prompt hash, asset sha256, ffprobe summary, each reviewer's scores and notes, verdict. Report failed takes alongside accepted ones.

Reject → `Store.invalidate_descendants(shot_id, shots)` so dependent edits are redone.
