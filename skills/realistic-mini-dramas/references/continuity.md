# Continuity contract rules

Enforced by `mini_drama.validate.continuity_errors` (run `./mini-drama validate`):

- Every shot belongs to the declared scene; every character id exists; every speaker is visible in the shot.
- Each visible character has a screen position and an eyeline.
- **180° axis:** the scene names a left character and a right character. The left one is never placed `right` and never looks `left`/`offscreen_left`; mirror for the right one.
- **Props:** `count_visible` never exceeds the scene inventory. A prop's holder sequence across shots is monotonic (one handoff, in the shot whose action is the handoff).
- Dependencies reference earlier shots only.
- Summed shot durations must be able to satisfy the project duration window.
- The structured prompt contains each dialogue line **verbatim, in double quotes**.

What to keep *outside* the provider prompt: a 3–6 line invariant list per shot (wardrobe, hair, prop count, axis, light) used only by QA.

Mutable vs immutable: expression, gesture, breath are mutable; id, age range, face/hair/wardrobe id, voice description are immutable (`forbidden_changes`). Changing an immutable field or a reference hash changes the operation key and voids descendant approvals.
