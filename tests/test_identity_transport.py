"""The chat application sends an email token only to approved API routes."""

import unittest

import httpx

from demo.transport import ChatTransport


class ChatTransportTests(unittest.TestCase):
    def test_token_and_route_gate_precedes_peer_transport(self):
        forwarded = []

        def respond(request):
            forwarded.append(request)
            return httpx.Response(200, json={"ok": True})

        with httpx.Client(
            transport=ChatTransport(httpx.MockTransport(respond), "user-token"),
            trust_env=False,
        ) as client:
            response = client.get(
                "https://example.test/v1/models",
                headers={"Authorization": "Bearer user-token"},
            )
            self.assertEqual(response.status_code, 200)
            with self.assertRaisesRegex(ValueError, "path is not allowed"):
                client.get(
                    "https://example.test/tee-report",
                    headers={"Authorization": "Bearer user-token"},
                )
            with self.assertRaisesRegex(ValueError, "authorization header"):
                client.get(
                    "https://example.test/v1/models",
                    headers={"Authorization": "Bearer other-token"},
                )

        self.assertEqual(len(forwarded), 1)
        self.assertEqual(forwarded[0].headers["authorization"], "Bearer user-token")


if __name__ == "__main__":
    unittest.main()
