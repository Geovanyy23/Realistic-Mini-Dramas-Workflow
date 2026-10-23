"""Fixture tests for the no-spend pilot. Run: python3 -m unittest discover -s tests -v
No network, no credentials, no provider spend."""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mini_drama import engine, providers, state, validate  # noqa: E402
from mini_drama.cli import main  # noqa: E402

PACK = ROOT / "examples" / "returned-key"


def load_pack():
    res = validate.validate_pack(PACK)
    assert res["ok"], res["errors"]
    return res["pack"]


def approve_everything(pack):
    """Mutate a copy so that generation_blockers() is empty (fixture only)."""
    p = copy.deepcopy(pack)
    p["project"]["model_label"].update({"observed": "fixture-observed-label", "identity_verified": True,
                                        "evidence_ref": "docs/capabilities.md#fixture"})
    p["project"]["capability_evidence"].update({"status": "audited", "audited_at": "2026-10-23T00:00:00Z"})
    p["project"]["budget_approved"].update({"approved": True, "approval_id": "appr-c"})
    p["project"]["content_rights"]["reference_rights_cleared"] = True
    for c in p["characters"]:
        for a in c["reference_assets"]:
            a["sha256"] = "a" * 64
            a["status"] = "approved"
    return p


def approvals(ch):
    return {g: {"id": g, "gate": g, "reviewer": "owner", "timestamp": "t", "contract_hash": ch,
                "scope": "fixture", "budget_note": "fixture"} for g in ("A_premise_budget", "B_references_locked", "C_spend")}


class TmpStore(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = state.Store(self.tmp / "state.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestContracts(TmpStore):
    def test_pack_validates_all_four_shots(self):
        pack = load_pack()
        self.assertEqual([s["id"] for s in pack["shots"]], ["S010", "S020", "S030", "S040"])

    def test_missing_identity_rejected(self):
        pack = load_pack()
        bad = copy.deepcopy(pack["characters"][0]); del bad["id"]
        self.assertTrue(validate.check_schema("character", bad))

    def test_minor_character_rejected(self):
        bad = copy.deepcopy(load_pack()["characters"][0]); bad["age_range"]["min"] = 16
        self.assertTrue(validate.check_schema("character", bad))

    def test_axis_cross_detected(self):
        pack = load_pack()
        shots = copy.deepcopy(pack["shots"]); shots[0]["eyelines"]["MARA"] = "left"
        errs = validate.continuity_errors(pack["project"], pack["characters"], pack["scene"], shots, pack["prompts"])
        self.assertTrue(any("axis" in e for e in errs))

    def test_one_key_through_all_shots(self):
        pack = load_pack()
        for s in pack["shots"]:
            if "KEY01" in s.get("prop_state", {}):
                self.assertEqual(s["prop_state"]["KEY01"]["count_visible"], 1)
        shots = copy.deepcopy(pack["shots"]); shots[3]["prop_state"]["KEY01"]["count_visible"] = 2
        errs = validate.continuity_errors(pack["project"], pack["characters"], pack["scene"], shots, pack["prompts"])
        self.assertTrue(any("exceeds inventory" in e for e in errs))

    def test_prompt_must_contain_verbatim_dialogue(self):
        pack = load_pack()
        prompts = copy.deepcopy(pack["prompts"]); prompts["S010"]["structured"] = prompts["S010"]["structured"].replace("leaving", "going")
        errs = validate.continuity_errors(pack["project"], pack["characters"], pack["scene"], pack["shots"], prompts)
        self.assertTrue(any("verbatim" in e for e in errs))

    def test_requested_model_label_preserved_unverified(self):
        ml = load_pack()["project"]["model_label"]
        self.assertEqual(ml["requested"], "Fable 5.1 for Claude")
        self.assertFalse(ml["identity_verified"]); self.assertIsNone(ml["observed"])


class TestGates(TmpStore):
    def test_unapproved_pack_blocks_every_shot(self):
        pack = load_pack()
        rep = engine.plan(pack, self.store, dry_run=True)
        self.assertTrue(rep["approval_needed"])
        for sid, b in rep["blockers"].items():
            self.assertTrue(b, sid)
            self.assertTrue(any("model identity" in x for x in b))
            self.assertTrue(any("Gate C" in x for x in b))
        self.assertTrue(all(a["state"] == "APPROVAL_NEEDED" for a in rep["attempts"]))

    def test_approved_fixture_has_no_blockers(self):
        pack = approve_everything(load_pack())
        self.store.data["approvals"] = approvals(state.contract_hash(pack))
        rep = engine.plan(pack, self.store, dry_run=True)
        self.assertFalse(rep["approval_needed"])

    def test_reference_hash_change_changes_operation_key(self):
        pack = approve_everything(load_pack())
        k1 = state.operation_key(pack["project"], pack["shots"][0], "p", pack["characters"], "rev")
        pack["characters"][0]["reference_assets"][0]["sha256"] = "b" * 64
        k2 = state.operation_key(pack["project"], pack["shots"][0], "p", pack["characters"], "rev")
        self.assertNotEqual(k1, k2)

    def test_operation_key_deterministic(self):
        pack = load_pack()
        a = state.operation_key(pack["project"], pack["shots"][0], "p", pack["characters"], "rev")
        b = state.operation_key(pack["project"], pack["shots"][0], "p", pack["characters"], "rev")
        self.assertEqual(a, b)


class TestIdempotencyAndRecovery(TmpStore):
    def _ready(self, fail_modes=None):
        pack = approve_everything(load_pack())
        self.store.data["approvals"] = approvals(state.contract_hash(pack))
        rep = engine.plan(pack, self.store, dry_run=False)
        self.store.data["dry_run"] = False
        prov = providers.FakeProvider(fail_modes=fail_modes or {})
        reqs = {a["shot_id"]: providers.SubmitRequest(a["operation_key"], a["shot_id"], "prompt", [], {}) for a in rep["attempts"]}
        return pack, prov, reqs

    def test_repeated_operation_key_submits_at_most_once(self):
        _, prov, reqs = self._ready()
        r = reqs["S010"]
        engine.submit_once(self.store, prov, r); engine.submit_once(self.store, prov, r); engine.submit_once(self.store, prov, r)
        self.assertEqual(prov.submissions.count(r.operation_key), 1)

    def test_concurrent_same_key_at_most_one_submission(self):
        _, prov, reqs = self._ready()
        r = reqs["S020"]
        errors = []
        def go():
            try: engine.submit_once(self.store, prov, r, holder=threading.current_thread().name)
            except Exception as e: errors.append(e)
        ts = [threading.Thread(target=go) for _ in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertLessEqual(prov.submissions.count(r.operation_key), 1)
        self.assertEqual(self.store.data["attempts"][r.operation_key]["state"], "SUBMITTED")

    def test_uncertain_after_click_reconciles_without_duplicate(self):
        _, prov, reqs = self._ready()
        r = reqs["S010"]; prov.fail_modes[r.operation_key] = "uncertain_submitted"
        a = engine.submit_once(self.store, prov, r)
        self.assertEqual(a["state"], "SUBMITTED"); self.assertIsNotNone(a["provider_job_id"])
        engine.submit_once(self.store, prov, r)
        self.assertEqual(prov.submissions.count(r.operation_key), 1)
        kinds = [e for e in self.store.data["events"] if e["kind"] == "transition" and e["to"] == "UNCERTAIN"]
        self.assertEqual(len(kinds), 1)

    def test_uncertain_before_click_returns_to_approved(self):
        _, prov, reqs = self._ready()
        r = reqs["S030"]; prov.fail_modes[r.operation_key] = "uncertain_not_submitted"
        a = engine.submit_once(self.store, prov, r)
        self.assertEqual(a["state"], "APPROVED"); self.assertEqual(prov.submissions.count(r.operation_key), 0)
        a = engine.submit_once(self.store, prov, r)  # explicit second call = the human-decided retry
        self.assertEqual(a["state"], "SUBMITTED"); self.assertEqual(prov.submissions.count(r.operation_key), 1)

    def test_crash_mid_submission_persists_and_reloads(self):
        _, prov, reqs = self._ready()
        r = reqs["S010"]; prov.fail_modes[r.operation_key] = "uncertain_submitted"
        engine.submit_once(self.store, prov, r)
        reloaded = state.Store(self.store.path)  # simulate process restart
        self.assertEqual(reloaded.data["attempts"][r.operation_key]["state"], "SUBMITTED")
        self.assertIsNone(reloaded.data["lease"])

    def test_auth_wall_blocks_without_terms(self):
        _, prov, reqs = self._ready()
        r = reqs["S010"]; prov.fail_modes[r.operation_key] = "auth_wall"
        a = engine.submit_once(self.store, prov, r)
        self.assertEqual(a["state"], "BLOCKED_AUTH"); self.assertEqual(prov.submissions, [])

    def test_real_adapter_never_runs_in_dry_mode(self):
        prov = providers.get_provider("videoexpress", dry_run=True)
        self.assertIsInstance(prov, providers.FakeProvider)
        self.store.data["dry_run"] = True
        real = providers.VideoExpressAdapter()
        req = providers.SubmitRequest("x" * 64, "S010", "p", [], {})
        self.store.data["attempts"][req.operation_key] = {"shot_id": "S010", "state": "APPROVED"}
        with self.assertRaises(RuntimeError):
            engine.submit_once(self.store, real, req)
        with self.assertRaises(providers.ProviderDisabled):
            real.submit(req)

    def test_rejected_shot_invalidates_dependents_only(self):
        pack, prov, reqs = self._ready()
        for sid in ("S010", "S020", "S030", "S040"):
            engine.submit_once(self.store, prov, reqs[sid])
            k = reqs[sid].operation_key
            for st in ("RUNNING", "DOWNLOADED", "QA_PENDING", "ACCEPTED"):
                self.store.transition(k, st)
        affected = self.store.invalidate_descendants("S020", pack["shots"])
        self.assertEqual(affected, ["S040"])
        self.assertEqual(self.store.data["attempts"][reqs["S040"].operation_key]["state"], "REJECTED")
        self.assertEqual(self.store.data["attempts"][reqs["S030"].operation_key]["state"], "ACCEPTED")

    def test_illegal_transition_rejected(self):
        _, prov, reqs = self._ready()
        with self.assertRaises(state.IllegalTransition):
            self.store.transition(reqs["S010"].operation_key, "ACCEPTED")


class TestMediaIntake(TmpStore):
    def _synthetic(self, name, audio=True):
        out = self.tmp / name
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=64x64:d=0.5"]
        if audio:
            cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=0.5"]
        cmd += ["-shortest", str(out)]
        subprocess.run(cmd, check=True)
        return out

    def test_html_disguised_as_mp4_rejected(self):
        p = self.tmp / "fake.mp4"; p.write_text("<html><body>Sign in</body></html>")
        with self.assertRaises(ValueError): engine.intake_asset(self.store, p, "S010", requires_audio=True)

    def test_empty_file_rejected(self):
        p = self.tmp / "empty.mp4"; p.write_bytes(b"")
        with self.assertRaises(ValueError): engine.intake_asset(self.store, p, "S010", requires_audio=True)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
    def test_missing_audio_rejected_when_dialogue_required(self):
        p = self._synthetic("silent.mp4", audio=False)
        with self.assertRaises(ValueError): engine.intake_asset(self.store, p, "S010", requires_audio=True)
        engine.intake_asset(self.store, p, "S040", requires_audio=False)  # S040 has no dialogue

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
    def test_valid_media_accepted_and_deduped_by_hash(self):
        p = self._synthetic("ok.mp4", audio=True)
        a = engine.intake_asset(self.store, p, "S010", requires_audio=True, provider_job_id="job-1")
        self.assertEqual(a["qa_status"], "unreviewed")
        a["qa_status"] = "accepted"; self.store.save()
        dup = self.tmp / "dup.mp4"; shutil.copy(p, dup)
        b = engine.intake_asset(self.store, dup, "S010", requires_audio=True)
        self.assertEqual(a["id"], b["id"]); self.assertEqual(len(self.store.data["assets"]), 1)


class TestPrivacyAndCli(TmpStore):
    def test_cli_validate_and_dry_run(self):
        self.assertEqual(main(["validate", str(PACK)]), 0)
        self.assertEqual(main(["plan", str(PACK), "--dry-run", "--state", str(self.tmp / "s.json")]), 0)
        self.assertTrue((self.tmp / "s.json").exists())
        self.assertEqual(main(["plan", str(PACK)]), 2)  # non-dry-run refused

    def test_package_has_no_private_leakage(self):
        from mini_drama.privacy import scan
        hits = [h for h in scan(ROOT) if not h.startswith(("examples/", "private/"))]  # private/ is git-ignored and never zipped
        self.assertEqual(hits, [], hits)

    def test_privacy_scan_catches_leaks(self):
        from mini_drama.privacy import scan
        (self.tmp / "private").mkdir(); (self.tmp / "private" / "transcript.txt").write_text("x")
        (self.tmp / "notes.md").write_text("api" + "_key = '" + "abcdefghijklmnopqrstuvwxyz'")
        (self.tmp / "frame.png").write_bytes(b"\x89PNG")
        hits = scan(self.tmp)
        self.assertEqual(len(hits), 3, hits)


if __name__ == "__main__":
    unittest.main()
