"""Unit tests for the withings-sync webhook exporter module."""

import io
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

import sys

# Temporarily isolate sys.argv so test runner flags (-s, -v) don't trigger sync.py's CLI parser on import
_orig_argv = sys.argv[:]
try:
    sys.argv = ["withings-sync"]
    from withings_sync import sync
finally:
    sys.argv = _orig_argv

from withings_sync.webhook import send_webhook


class TestWebhookModule(unittest.TestCase):
    """Test suite for withings_sync.webhook.send_webhook."""

    def test_send_webhook_empty_url(self):
        """Should return False and not attempt connection if url is empty."""
        result = send_webhook(url="", payload={"data": 123})
        self.assertFalse(result)

    @patch("urllib.request.urlopen")
    def test_send_webhook_success(self, mock_urlopen):
        """Should send JSON POST request and return True on 200 OK."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status": "success"}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        payload = {"data": {"weight": 70.5}}
        url = "https://example.com/webhook"

        result = send_webhook(url=url, payload=payload)
        self.assertTrue(result)

        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_full_url(), url)
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.headers.get("Content-type"), "application/json; charset=utf-8")
        self.assertEqual(req.headers.get("User-agent"), "withings-sync")

        sent_body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(sent_body, payload)

    @patch("urllib.request.urlopen")
    def test_send_webhook_with_secret(self, mock_urlopen):
        """Should attach X-Webhook-Secret header and include secret in payload."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"OK"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        payload = {"measurements": [1, 2, 3]}
        secret = "my-secret-key-123"
        url = "https://script.google.com/macros/s/xyz/exec"

        result = send_webhook(url=url, payload=payload, secret=secret)
        self.assertTrue(result)

        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.headers.get("X-webhook-secret"), secret)

        sent_body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(sent_body.get("secret"), secret)
        self.assertEqual(sent_body.get("measurements"), [1, 2, 3])

    @patch("urllib.request.urlopen")
    def test_send_webhook_http_error(self, mock_urlopen):
        """Should catch HTTPError, log it, and return False."""
        fp = io.BytesIO(b"Forbidden")
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://example.com/webhook",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=fp,
        )

        result = send_webhook(url="https://example.com/webhook", payload={"test": 1})
        self.assertFalse(result)

    @patch("urllib.request.urlopen")
    def test_send_webhook_url_error(self, mock_urlopen):
        """Should catch URLError (network failure) and return False."""
        mock_urlopen.side_effect = urllib.error.URLError(reason="Name resolution failed")

        result = send_webhook(url="https://invalid-host-domain.test/webhook", payload={})
        self.assertFalse(result)


class TestSyncCliArguments(unittest.TestCase):
    """Test CLI argument parsing for webhook options in sync.py."""

    @patch("sys.argv", ["withings-sync", "--webhook-url", "https://example.com/hook", "--webhook-secret", "sec123"])
    def test_get_args_webhook_flags(self):
        """Should parse --webhook-url and --webhook-secret flags."""
        args = sync.get_args()
        self.assertEqual(args.webhook_url, "https://example.com/hook")
        self.assertEqual(args.webhook_secret, "sec123")


class TestSyncWebhookIntegration(unittest.TestCase):
    """Test sync() integration with webhook sending."""

    @patch("withings_sync.sync.send_webhook")
    @patch("withings_sync.sync.WithingsAccount")
    @patch("withings_sync.sync.generate_fitdata")
    @patch("withings_sync.sync.generate_jsondata")
    @patch("withings_sync.sync.write_to_file_when_needed")
    def test_sync_invokes_webhook_when_url_provided(
        self,
        mock_write_files,
        mock_gen_json,
        mock_gen_fit,
        mock_withings_cls,
        mock_send_webhook,
    ):
        """sync() should call send_webhook with proper payload when webhook_url is set."""
        mock_withings = MagicMock()
        mock_withings.get_height.return_value = 1.75
        mock_group = MagicMock()
        mock_group.attrib = {"date": 1700000000}
        mock_withings.get_measurements.return_value = [mock_group]
        raw_json_data = {"status": 0, "body": {"measuregrps": []}}
        mock_withings.last_measurements_json = raw_json_data
        mock_withings_cls.return_value = mock_withings

        mock_gen_fit.return_value = (None, None)
        mock_gen_json.return_value = None

        with patch.object(sync.ARGS, "webhook_url", "https://example.com/endpoint"), \
             patch.object(sync.ARGS, "webhook_secret", "secret456"), \
             patch.object(sync.ARGS, "dump_raw", False), \
             patch.object(sync.ARGS, "no_upload", True), \
             patch.object(sync.ARGS, "fromdate", None), \
             patch.object(sync.ARGS, "todate", sync.date(2026, 9, 27)), \
             patch.object(sync.ARGS, "trainerroad_username", None), \
             patch.object(sync.ARGS, "garmin_username", None), \
             patch.object(sync.ARGS, "features", []):
            
            with patch("withings_sync.sync.prepare_syncdata") as mock_prep:
                mock_prep.return_value = ("weight", 1700000000, [{"type": "weight", "date_time": 1700000000}])
                
                result = sync.sync()
                self.assertEqual(result, 0)

                mock_send_webhook.assert_called_once()
                call_kwargs = mock_send_webhook.call_args[1]
                self.assertEqual(call_kwargs["url"], "https://example.com/endpoint")
                self.assertEqual(call_kwargs["secret"], "secret456")
                payload = call_kwargs["payload"]
                self.assertEqual(payload["source"], "withings-sync")
                self.assertEqual(payload["data"], raw_json_data)
                self.assertTrue(payload["filename"].startswith("withings_raw_"))


if __name__ == "__main__":
    unittest.main()
