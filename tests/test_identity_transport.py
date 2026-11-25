"""Application credentials are released only through the admitted transport."""

import unittest
from unittest.mock import Mock

import httpx

from demo.transport import AppraisedTransport, SDK_PLACEHOLDER_API_KEY


class IdentityTransportTests(unittest.TestCase):
    def test_replaces_sdk_placeholder_only_for_chat_api(self):
        session = Mock()
        session.request.return_value = (200, [], b"{}")
        transport = AppraisedTransport(session, "test-access-token")
        request = httpx.Request("GET", "https://match.demo.genxt.network/v1/models",
                                headers={"Authorization": "Bearer " + SDK_PLACEHOLDER_API_KEY})
        self.assertEqual(transport.handle_request(request).status_code, 200)
        headers = session.request.call_args.args[2]
        self.assertIn(("authorization", "Bearer test-access-token"), headers)
        self.assertNotIn(("authorization", "Bearer " + SDK_PLACEHOLDER_API_KEY), headers)

    def test_rejects_unapproved_path_and_credentials(self):
        session = Mock()
        transport = AppraisedTransport(session, "test-access-token")
        with self.assertRaises(ValueError):
            transport.handle_request(httpx.Request("GET", "https://match.demo.genxt.network/tee-report"))
        with self.assertRaises(ValueError):
            transport.handle_request(
                httpx.Request(
                    "GET", "https://match.demo.genxt.network/v1/models",
                    headers={"Authorization": "Bearer other"},
                )
            )
        session.request.assert_not_called()
