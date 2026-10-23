"""Deterministic state engine: operation keys, attempt state machine,
atomic JSON store, approval gates and reconciliation.

Nothing here talks to a network. Providers are injected (see providers.py).
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

STATES = ["PLANNED", "APPROVAL_NEEDED", "APPROVED", "SUBMITTING", "UNCERTAIN", "SUBMITTED",
          "RUNNING", "DOWNLOADED", "QA_PENDING", "ACCEPTED", "REJECTED",
          "BLOCKED_AUTH", "BLOCKED_MODEL", "FAILED"]

TRANSITIONS = {
    "PLANNED": {"APPROVAL_NEEDED", "APPROVED", "BLOCKED_MODEL"},
    "APPROVAL_NEEDED": {"APPROVED", "REJECTED"},
    "APPROVED": {"SUBMITTING", "BLOCKED_AUTH", "BLOCKED_MODEL"},
    "SUBMITTING": {"SUBMITTED", "UNCERTAIN", "BLOCKED_AUTH", "FAILED"},
    "UNCERTAIN": {"SUBMITTED", "FAILED", "APPROVED"},  # APPROVED only after reconcile says 'not submitted'
    "SUBMITTED": {"RUNNING", "FAILED", "UNCERTAIN"},
    "RUNNING": {"DOWNLOADED", "FAILED"},
    "DOWNLOADED": {"QA_PENDING", "FAILED"},
    "QA_PENDING": {"ACCEPTED", "REJECTED"},
    "ACCEPTED": {"REJECTED"},  # a later review may still reject
    "REJECTED": set(),
    "BLOCKED_AUTH": {"APPROVED"},
    "BLOCKED_MODEL": {"PLANNED"},
    "FAILED": {"APPROVED"},  # retry only via explicit approval
}

MAX_READ_RETRIES = 3


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def contract_hash(pack: dict) -> str:
    """Hash of the locked inputs (project, characters, scene, shots, prompts)."""
    return sha256_text(canonical({k: pack[k] for k in ("project", "characters", "scene", "shots", "prompts")}))


def operation_key(project: dict, shot: dict, prompt_text: str, characters: list, approved_revision: str) -> str:
    """hash(project + shot + prompt + canonical references + observed model/settings + approved revision)"""
    refs = sorted(
        ({"asset_id": a["asset_id"], "sha256": a["sha256"]}
         for c in characters if c["id"] in shot["character_ids"] for a in c["reference_assets"]
         if a["asset_id"] in shot["reference_asset_ids"]),
        key=lambda r: r["asset_id"])
    material = {
        "project_id": project["id"],
        "shot_id": shot["id"],
        "prompt": prompt_text,
        "references": refs,
        "model": project["model_label"],
        "observed_settings": shot["observed_settings"],
        "approved_revision": approved_revision,
    }
    return sha256_text(canonical(material))


class IllegalTransition(Exception):
    pass


class Store:
    """Atomic JSON state file with an in-process lock.

    Layout: {"project_id", "contract_hash", "dry_run", "attempts": {op_key: attempt},
             "assets": {asset_id: asset}, "approvals": {id: approval}, "events": [...]}
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self.data = self._load()

    def _load(self):
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"project_id": None, "contract_hash": None, "dry_run": True,
                "attempts": {}, "assets": {}, "approvals": {}, "lease": None, "events": []}

    def save(self):
        """Atomic write: temp file in the same directory, fsync, rename."""
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".state-", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)

    def event(self, kind: str, **kw):
        self.data["events"].append({"t": now(), "kind": kind, **kw})

    # ------------------------------------------------------------ attempts
    def get_or_plan(self, op_key: str, shot_id: str, dry_run: bool) -> dict:
        with self._lock:
            a = self.data["attempts"].get(op_key)
            if a is None:
                a = {"id": f"att-{op_key[:12]}", "shot_id": shot_id, "operation_key": op_key,
                     "state": "PLANNED", "started_at": None, "finished_at": None,
                     "provider_job_id": None, "evidence_before": None, "evidence_after": None,
                     "cost_if_visible": None, "failure_class": None, "retry_count": 0,
                     "chosen_take": False, "reviewer": None, "dry_run": dry_run}
                self.data["attempts"][op_key] = a
                self.event("planned", op_key=op_key, shot_id=shot_id)
                self.save()
            return a

    def transition(self, op_key: str, new_state: str, **fields) -> dict:
        with self._lock:
            a = self.data["attempts"][op_key]
            if new_state not in TRANSITIONS.get(a["state"], set()):
                raise IllegalTransition(f"{a['shot_id']}: {a['state']} -> {new_state} not allowed")
            old = a["state"]
            a["state"] = new_state
            a.update(fields)
            if new_state in ("ACCEPTED", "REJECTED", "FAILED"):
                a["finished_at"] = now()
            self.event("transition", op_key=op_key, **{"from": old, "to": new_state})
            self.save()
            return a

    # ------------------------------------------------------------ lease
    def acquire_lease(self, holder: str) -> bool:
        """Account-wide lease: one submission in flight at a time."""
        with self._lock:
            if self.data["lease"] and self.data["lease"]["holder"] != holder:
                return False
            self.data["lease"] = {"holder": holder, "at": now()}
            self.save()
            return True

    def release_lease(self, holder: str):
        with self._lock:
            if self.data["lease"] and self.data["lease"]["holder"] == holder:
                self.data["lease"] = None
                self.save()

    # ------------------------------------------------------------ invalidation
    def invalidate_descendants(self, shot_id: str, shots: list):
        """A rejected/changed shot invalidates attempts and assets of dependent shots."""
        with self._lock:
            deps = {s["id"]: set(s["dependencies"]) for s in shots}
            affected, frontier = set(), {shot_id}
            while frontier:
                nxt = {sid for sid, d in deps.items() if d & frontier} - affected
                affected |= nxt
                frontier = nxt
            for a in self.data["attempts"].values():
                if a["shot_id"] in affected and a["state"] in ("ACCEPTED", "QA_PENDING", "DOWNLOADED", "APPROVED"):
                    a["state"] = "REJECTED"
                    a["failure_class"] = "content_model_mismatch"
                    a["chosen_take"] = False
            for asset in self.data["assets"].values():
                if asset.get("source_shot") in affected and asset["qa_status"] == "accepted":
                    asset["qa_status"] = "invalidated"
            self.event("invalidate", root=shot_id, affected=sorted(affected))
            self.save()
            return sorted(affected)


# ------------------------------------------------------------------ gates
def generation_blockers(project: dict, characters: list, shot: dict, approvals: dict) -> list[str]:
    """Reasons a shot may NOT be sent to a real provider. Empty list == allowed."""
    b = []
    ml = project["model_label"]
    policy = ml.get("selection_policy", "exact_model")
    if policy not in {"exact_model", "live_default"}:
        b.append("invalid model selection policy")
    if policy != "live_default" and (not ml["identity_verified"] or not ml["observed"]):
        b.append(f"model identity unverified (requested {ml['requested']!r}, observed {ml['observed']!r})")
    if project["capability_evidence"]["status"] != "audited":
        b.append(f"capability audit status is {project['capability_evidence']['status']!r}, needs 'audited'")
    if not project["budget_approved"]["approved"] or not project["budget_approved"]["approval_id"]:
        b.append("spend not approved (Gate C)")
    if not project["content_rights"]["reference_rights_cleared"]:
        b.append("reference rights not cleared")
    for c in characters:
        if c["id"] in shot["character_ids"]:
            for a in c["reference_assets"]:
                if a["asset_id"] in shot["reference_asset_ids"] and (a["sha256"] is None or a.get("status") != "approved"):
                    b.append(f"{c['id']} reference {a['asset_id']} is a placeholder, not an approved asset with sha256")
    needed = {"A_premise_budget", "B_references_locked", "C_spend"}
    have = {ap["gate"] for ap in approvals.values()}
    for g in sorted(needed - have):
        b.append(f"missing approval gate {g}")
    return b
