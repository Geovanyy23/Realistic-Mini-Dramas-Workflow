# State, idempotency and recovery

Operation key = sha256(project id + shot id + prompt + sorted reference asset ids/hashes + model label + observed settings + approved revision). Same inputs → same key → at most one physical submission, ever.

States: PLANNED → APPROVAL_NEEDED/APPROVED → SUBMITTING → SUBMITTED → RUNNING → DOWNLOADED → QA_PENDING → ACCEPTED/REJECTED, plus UNCERTAIN, BLOCKED_AUTH, BLOCKED_MODEL, FAILED. Transitions are whitelisted in `state.TRANSITIONS`; anything else raises.

- The state file is written atomically (temp file + fsync + rename) after every transition.
- `submit_once` acquires a single account lease (max_concurrent_jobs = 1), moves to SUBMITTING, calls the adapter once, and releases the lease in `finally`.
- A timeout → UNCERTAIN → `reconcile()` reads provider history: found → SUBMITTED with the job id; absent → back to APPROVED, and only a new explicit call retries. Never auto-loop.
- Transport read/poll retries: bounded backoff, max 3. Generation failures: at most 2 approved attempts per shot.
- Dry run (`store.dry_run = True`) refuses any adapter with `real = True`; `get_provider(..., dry_run=True)` always returns the fake.
- `VideoExpressAdapter` is constructed disabled; it only runs when the owner arms it inside an approved live run and a dedicated tab controller is injected.
- Downloads must be non-empty, ffprobe-readable, contain video (and audio when the shot has dialogue), and are deduplicated by sha256 without overwriting an accepted take.
