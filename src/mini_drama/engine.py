"""Orchestration: plan attempts, submit exactly once per operation key,
reconcile uncertain outcomes, intake assets."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from .providers import AuthWall, Provider, SubmitRequest, SubmitUncertain
from .state import Store, contract_hash, generation_blockers, now, operation_key


def plan(pack: dict, store: Store, dry_run: bool, approved_revision: str | None = None) -> dict:
    """Create/refresh PLANNED attempts for every shot. Returns the approval-needed report."""
    project, characters, shots, prompts = pack["project"], pack["characters"], pack["shots"], pack["prompts"]
    ch = contract_hash(pack)
    rev = approved_revision or ch
    store.data["project_id"] = project["id"]
    store.data["contract_hash"] = ch
    store.data["dry_run"] = dry_run
    report = {"project": project["id"], "contract_hash": ch, "dry_run": dry_run,
              "model_label_requested": project["model_label"]["requested"],
              "model_identity_verified": project["model_label"]["identity_verified"],
              "retry_ceiling_per_shot": project["budget_approved"]["max_attempts_per_shot"],
              "max_concurrent_jobs": project["budget_approved"]["max_concurrent_jobs"],
              "planned_output_count": len(shots), "attempts": [], "blockers": {}}
    for s in sorted(shots, key=lambda x: x["ordinal"]):
        prompt = prompts[s["id"]]["structured"]
        ok = operation_key(project, s, prompt, characters, rev)
        a = store.get_or_plan(ok, s["id"], dry_run)
        blockers = generation_blockers(project, characters, s, store.data["approvals"])
        if a["state"] == "PLANNED":
            store.transition(ok, "APPROVAL_NEEDED" if blockers else "APPROVED")
        report["attempts"].append({"shot_id": s["id"], "operation_key": ok, "state": a["state"],
                                   "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                                   "references": s["reference_asset_ids"],
                                   "duration_requested_s": s["duration_requested_s"],
                                   "visible_cost": None, "plan_terms": None})
        report["blockers"][s["id"]] = blockers
    report["approval_needed"] = any(report["blockers"].values())
    store.event("plan", dry_run=dry_run)
    store.save()
    return report


def submit_once(store: Store, provider: Provider, req: SubmitRequest, holder: str = "operator") -> dict:
    """Submit an APPROVED attempt exactly once. Idempotent on operation key.
    Returns the attempt record. Never runs a real adapter in dry mode."""
    a = store.data["attempts"][req.operation_key]
    if store.data["dry_run"] and provider.real:
        raise RuntimeError("real provider in dry run — refusing")
    if a["state"] in ("SUBMITTED", "RUNNING", "DOWNLOADED", "QA_PENDING", "ACCEPTED"):
        return a  # already physically submitted; do nothing
    if a["state"] == "UNCERTAIN":
        return reconcile(store, provider, req.operation_key)
    if a["state"] != "APPROVED":
        raise RuntimeError(f"{a['shot_id']}: cannot submit from state {a['state']}")
    if not store.acquire_lease(holder):
        raise RuntimeError("account lease held by another operator; one job at a time")
    try:
        store.transition(req.operation_key, "SUBMITTING", started_at=now(), evidence_before="pre-submit snapshot")
        try:
            receipt = provider.submit(req)
        except SubmitUncertain as e:
            store.transition(req.operation_key, "UNCERTAIN", evidence_after=str(e))
            return reconcile(store, provider, req.operation_key)
        except AuthWall as e:
            store.transition(req.operation_key, "BLOCKED_AUTH", failure_class="auth_terms_payment", evidence_after=str(e))
            return store.data["attempts"][req.operation_key]
        return store.transition(req.operation_key, "SUBMITTED",
                                provider_job_id=receipt.provider_job_id, evidence_after=receipt.evidence)
    finally:
        store.release_lease(holder)


def reconcile(store: Store, provider: Provider, op_key: str) -> dict:
    """Resolve an UNCERTAIN attempt by reading provider history. Never resubmits blindly."""
    a = store.data["attempts"][op_key]
    if a["state"] != "UNCERTAIN":
        return a
    for job in provider.history():
        if job.get("operation_key") == op_key or job.get("shot_id") == a["shot_id"] and job.get("provider_job_id") == a.get("provider_job_id"):
            return store.transition(op_key, "SUBMITTED", provider_job_id=job["provider_job_id"],
                                    evidence_after="reconciled from history")
    # Not found in history: it was not submitted. Return to APPROVED; a human/caller decides to retry.
    return store.transition(op_key, "APPROVED", evidence_after="reconciled: absent from history")


def ffprobe(path: Path) -> dict | None:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
                             capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def intake_asset(store: Store, path: Path, source_shot: str, requires_audio: bool, provider_job_id=None,
                 provenance="provider_output") -> dict:
    """Validate a downloaded file before it can be bound to a shot.
    Rejects: missing/empty file, non-media (e.g. HTML disguised as MP4), missing audio when dialogue required."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError("empty or missing file")
    probe = ffprobe(path)
    if not probe or not probe.get("streams"):
        raise ValueError("ffprobe could not read media (not a valid video file)")
    kinds = {s.get("codec_type") for s in probe["streams"]}
    if "video" not in kinds:
        raise ValueError("no video stream")
    if requires_audio and "audio" not in kinds:
        raise ValueError("dialogue shot has no audio stream")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    for existing in store.data["assets"].values():
        if existing["sha256"] == digest and existing["qa_status"] == "accepted":
            return existing  # dedupe by hash; never overwrite an accepted take
    asset = {"id": f"asset-{digest[:12]}", "relative_path": str(path), "sha256": digest, "provenance": provenance,
             "rights": "owner-generated, original story", "provider_job_id": provider_job_id,
             "source_shot": source_shot, "created_at": now(),
             "ffprobe": {"streams": [{"codec_type": s.get("codec_type"), "codec_name": s.get("codec_name"),
                                      "width": s.get("width"), "height": s.get("height"),
                                      "r_frame_rate": s.get("r_frame_rate")} for s in probe["streams"]],
                         "duration": probe.get("format", {}).get("duration")},
             "qa_status": "unreviewed"}
    store.data["assets"][asset["id"]] = asset
    store.save()
    return asset
