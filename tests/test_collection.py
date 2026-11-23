"""Caller retrieval guards; mocked HTTP, no hardware assertions."""
import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock
import httpx
from demo import collection, admission

class CollectionTests(unittest.TestCase):
    def setUp(self):collection._cache.clear()
    def test_transient_kds_retry_and_cache(self):
        url=collection.KDS+'/cert_chain'
        error=httpx.HTTPStatusError('retry',request=httpx.Request('GET',url),response=httpx.Response(429,headers={'retry-after':'0'}))
        with patch.object(collection,'fetch',side_effect=[error,(b'raw signed data',{})]) as fetch, patch.object(collection.time,'sleep'):
            self.assertEqual(collection.kds(url),b'raw signed data')
            self.assertEqual(collection.kds(url),b'raw signed data')
            self.assertEqual(fetch.call_count,2)
    def test_retry_bound_and_excessive_retry_after(self):
        url=collection.KDS+'/cert_chain'
        for delay,count in [('0',3),('61',1)]:
            error=httpx.HTTPStatusError('retry',request=httpx.Request('GET',url),response=httpx.Response(503,headers={'retry-after':delay}))
            with patch.object(collection,'fetch',side_effect=error) as fetch, patch.object(collection.time,'sleep'):
                with self.assertRaises((httpx.HTTPStatusError,ValueError)):collection.kds(url)
                self.assertEqual(fetch.call_count,count)
    def test_nonce_log_matches_report_request(self):
        nonce = bytes(range(32))
        encoded = base64.b64encode(nonce).decode()
        messages = []
        with patch.object(collection.secrets, 'token_bytes', return_value=nonce), patch.object(collection, 'fetch', side_effect=RuntimeError('request intercepted')) as fetch:
            with self.assertRaisesRegex(RuntimeError, 'request intercepted'):
                collection.collect_and_verify({'origin': 'https://example.test'}, progress=messages.append)
        self.assertEqual(fetch.call_args.args[0], 'https://example.test/tee-report')
        self.assertEqual(fetch.call_args.kwargs['body'], {'nonce': encoded})
        self.assertTrue(any('sending nonce in JSON body' in message and encoded in message for message in messages))

    def test_evidence_failure_never_constructs_transport(self):
        with patch.object(admission,'Session') as session:
            with self.assertRaises(ValueError):admission.authenticate({}, {'scope':'evidence_only','status':'policy_mismatch'})
            session.assert_not_called()
    def test_peer_probe_uses_direct_endpoint_without_credentials(self):
        app={'origin':'https://example.test'}
        result={'scope':'evidence_only','status':'verified','verified_artifacts':{'certificate_der_base64':base64.b64encode(b'cert').decode()}}
        run=Mock()
        with patch.object(admission,'Session') as factory:
            factory.return_value.request.return_value=(204,[],b'')
            admission.authenticate(app,result,run=run)
            factory.assert_called_once_with(app['origin'],b'cert')
            factory.return_value.request.assert_called_once_with('HEAD','https://example.test/tee-report',[],b'')
            factory.return_value.request.return_value=(405,[],b'')
            with self.assertRaisesRegex(ValueError,'endpoint unavailable'):
                admission.authenticate(app,result,run=run)
    def test_policy_cannot_escape_local_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'app.json';path.write_text(json.dumps({'schema_version':2,'origin':'https://example.test','verifier_policy':'../outside.json'}))
            with self.assertRaisesRegex(ValueError,'local'):collection.load_policy(path)
