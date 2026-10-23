"""Model metadata is optional only for an explicitly selected live workflow."""
import unittest
from test_pilot import load_pack, approve_everything, approvals
from mini_drama import state, validate

class ModelPolicyTests(unittest.TestCase):
    def blockers(self, pack):
        return state.generation_blockers(pack['project'], pack['characters'], pack['shots'][0], approvals(state.contract_hash(pack)))

    def prepared(self):
        p = approve_everything(load_pack())
        p['project']['model_label'].update(observed=None, identity_verified=False, selection_policy='live_default')
        return p

    def test_audited_live_default_accepts_hidden_identity_without_faking_it(self):
        p = self.prepared()
        self.assertEqual([], self.blockers(p))
        self.assertFalse(p['project']['model_label']['identity_verified'])
        self.assertEqual([], validate.check_schema('project', p['project']))

    def test_explicit_exact_model_still_blocks(self):
        p = self.prepared()
        p['project']['model_label']['selection_policy'] = 'exact_model'
        self.assertTrue(any('model identity' in b for b in self.blockers(p)))

    def test_legacy_omission_still_blocks(self):
        p = self.prepared()
        del p['project']['model_label']['selection_policy']
        self.assertTrue(any('model identity' in b for b in self.blockers(p)))

    def test_live_default_requires_audit_and_budget_approval(self):
        p = self.prepared()
        p['project']['capability_evidence']['status'] = 'not_audited'
        p['project']['budget_approved']['approved'] = False
        blockers = self.blockers(p)
        self.assertTrue(any('capability audit' in b for b in blockers))
        self.assertTrue(any('spend not approved' in b for b in blockers))

    def test_unknown_policy_fails_closed(self):
        p = self.prepared()
        p['project']['model_label']['selection_policy'] = 'typo'
        self.assertIn('invalid model selection policy', self.blockers(p))
