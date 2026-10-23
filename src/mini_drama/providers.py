"""Provider adapters.

- Provider: the interface.
- FakeProvider: in-memory; can simulate uncertain submit (crash after click,
  before id receipt), reconciliation via history, auth walls and failures.
- VideoExpressAdapter: the real adapter *skeleton*. It is disabled by default
  and raises on any call unless explicitly armed by the owner at runtime.
  It never runs in dry mode. No private endpoints; browser locators must be
  observed live (see skills/realistic-mini-dramas/references/browser.md).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


class SubmitUncertain(Exception):
    """Submission outcome unknown (timeout / crash after click). Reconcile before retry."""


class AuthWall(Exception):
    """Login/terms/payment wall encountered. Record BLOCKED_AUTH, never accept terms."""


class ProviderDisabled(RuntimeError):
    pass


@dataclass
class SubmitRequest:
    operation_key: str
    shot_id: str
    prompt: str
    reference_asset_ids: list
    settings: dict


@dataclass
class SubmitReceipt:
    provider_job_id: str
    evidence: str


class Provider:
    name = "base"
    real = False  # True only for adapters that can spend money

    def capability_report(self) -> dict:
        raise NotImplementedError

    def submit(self, req: SubmitRequest) -> SubmitReceipt:
        raise NotImplementedError

    def history(self) -> list[dict]:
        """Visible provider history. Used to reconcile UNCERTAIN submissions."""
        raise NotImplementedError

    def poll(self, provider_job_id: str) -> str:
        raise NotImplementedError


@dataclass
class FakeProvider(Provider):
    """Deterministic fake. `fail_mode` per operation key:
       None | 'uncertain_submitted' | 'uncertain_not_submitted' | 'auth_wall' | 'generation_failed'
    `uncertain_submitted` raises SubmitUncertain but the job WAS recorded in history.
    `uncertain_not_submitted` raises SubmitUncertain and nothing was recorded."""
    name: str = "fake"
    real: bool = False
    fail_modes: dict = field(default_factory=dict)
    jobs: dict = field(default_factory=dict)          # provider_job_id -> record
    submissions: list = field(default_factory=list)   # every physical submission

    def capability_report(self) -> dict:
        return {"provider": "fake", "model_label": "fake-model", "audited_at": "n/a",
                "controls": {"image_prompt": True, "audio_input": False, "reference_slots": 2}}

    def _job_id(self, req: SubmitRequest) -> str:
        return "job-" + hashlib.sha256(req.operation_key.encode()).hexdigest()[:10]

    def submit(self, req: SubmitRequest) -> SubmitReceipt:
        mode = self.fail_modes.get(req.operation_key)
        if mode == "auth_wall":
            raise AuthWall("login wall")
        jid = self._job_id(req)
        if mode == "uncertain_not_submitted":
            self.fail_modes[req.operation_key] = None  # next attempt behaves normally
            raise SubmitUncertain("timeout before click registered")
        # physical submission happens here
        self.submissions.append(req.operation_key)
        self.jobs[jid] = {"provider_job_id": jid, "operation_key": req.operation_key,
                          "shot_id": req.shot_id, "status": "failed" if mode == "generation_failed" else "running"}
        if mode == "uncertain_submitted":
            self.fail_modes[req.operation_key] = None
            raise SubmitUncertain("timeout after click; id never received")
        return SubmitReceipt(provider_job_id=jid, evidence="fake-toast")

    def history(self) -> list[dict]:
        return list(self.jobs.values())

    def poll(self, provider_job_id: str) -> str:
        return self.jobs[provider_job_id]["status"]


class VideoExpressAdapter(Provider):
    """Real adapter skeleton. Disabled until the owner arms it at runtime AND
    the capability audit is 'audited'. Even then it only maps to live-observed
    semantic controls; nothing here encodes private endpoints."""
    name = "videoexpress"
    real = True
    EDITOR_ORIGIN_HISTORICAL = "https://app.videoexpress.ai/"  # historical 2026-07-31; reconfirm live

    def __init__(self, armed: bool = False, browser=None):
        self.armed = armed
        self.browser = browser  # a dedicated-tab controller injected by the operator

    def _guard(self):
        if not self.armed:
            raise ProviderDisabled("VideoExpressAdapter is disabled; arm it only in an owner-approved live run")
        if self.browser is None:
            raise ProviderDisabled("no dedicated browser tab controller was provided")

    def capability_report(self) -> dict:
        self._guard()
        raise NotImplementedError("Implement from LIVE observation only: model label, controls, durations, "
                                  "ratios, reference slots, sharing checkbox, queue/job identity.")

    def submit(self, req: SubmitRequest) -> SubmitReceipt:
        self._guard()
        raise NotImplementedError("Submit exactly once per operation key; record receipt; UNCERTAIN on timeout.")

    def history(self) -> list[dict]:
        self._guard()
        raise NotImplementedError("Read My AI Videos / queue cards via supported UI only.")

    def poll(self, provider_job_id: str) -> str:
        self._guard()
        raise NotImplementedError


def get_provider(name: str, dry_run: bool, **kw) -> Provider:
    if dry_run:
        # A real adapter is NEVER constructed in dry mode.
        return FakeProvider(**kw)
    if name == "fake":
        return FakeProvider(**kw)
    if name == "videoexpress":
        return VideoExpressAdapter(**kw)
    raise ProviderDisabled(f"no adapter for {name!r}; api/local adapters are not implemented and need separate authorization")
