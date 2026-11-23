"""Live admission context tests use local synthetic inputs, never hardware claims."""
import base64
import copy
import hashlib
import unittest
from unittest.mock import patch
from demo.run import LiveRun
from demo import admission


def make_run():
    digest = lambda b: hashlib.sha256(b).hexdigest()
    policy = b'local policy'
    inputs = {name: base64.b64encode(name.encode()).decode() for name in ('report', 'amd_chain', 'vcek', 'reference')}
    context = {'expected_nonce_base64': base64.b64encode(bytes(range(32))).decode(), 'evaluation_unix_seconds': 1}
    app = {'origin': 'https://example.test', 'verifier_bytes': policy}
    result = {'scope': 'evidence_only', 'status': 'verified', 'expected_nonce_base64': context['expected_nonce_base64'],
              'evaluated_at': 1, 'policy_sha256': digest(policy), 'report_sha256': digest(b'report'),
              'input_sha256': {key: digest(name.encode()) for name, key in
                              [('amd_chain', 'amd_chain_pem'), ('vcek', 'vcek_der'), ('reference', 'reference_json')]}}
    archive = {'mode': 'live_collection', 'origin': app['origin'], 'inputs': inputs, 'context': context}
    return app, LiveRun(result, archive, 100, digest(policy), {})


class LiveRunTests(unittest.TestCase):
    def test_live_result_is_one_use_and_deadline_is_monotonic(self):
        app, run = make_run()
        with patch('demo.run.time.monotonic', return_value=99):
            run.ensure_current(app, run.result)
            run.consume(app, run.result)
            with self.assertRaisesRegex(ValueError, 'already been used'):
                run.consume(app, run.result)
        app, run = make_run()
        with patch('demo.run.time.monotonic', return_value=100):
            with self.assertRaisesRegex(ValueError, 'deadline expired'):
                run.ensure_current(app, run.result)

    def test_origin_policy_inputs_result_and_context_cannot_be_replaced(self):
        changes = [lambda a,r: a.update(origin='https://other.test'),
                   lambda a,r: a.update(verifier_bytes=b'other policy'),
                   lambda a,r: r.result.update(report_sha256='0'*64),
                   lambda a,r: r.archive['inputs'].update(vcek='YWJj'),
                   lambda a,r: r.archive['context'].update(evaluation_unix_seconds=2),
                   lambda a,r: r.archive.update(mode='historical_replay')]
        for change in changes:
            app, run = make_run()
            change(app, run)
            with patch('demo.run.time.monotonic', return_value=99), self.assertRaises(ValueError):
                run.ensure_current(app, run.result)

    def test_independent_context_must_match_result_even_at_construction(self):
        for field, value in [('expected_nonce_base64', 'bad'), ('evaluated_at', 2), ('policy_sha256', '0'*64)]:
            app, old = make_run()
            result = copy.deepcopy(old.result); result[field] = value
            run = LiveRun(result, old.archive, 100, old.policy_sha256, {})
            with patch('demo.run.time.monotonic', return_value=99), self.assertRaises(ValueError):
                run.ensure_current(app, result)

    def test_saved_result_without_live_context_cannot_construct_transport(self):
        app, run = make_run()
        with patch.object(admission, 'Session') as session:
            with self.assertRaisesRegex(ValueError, 'Live'):
                admission.authenticate(app, {}, run.result)
            session.assert_not_called()
