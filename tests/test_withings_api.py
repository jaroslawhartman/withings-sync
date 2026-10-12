"""Regression tests for API retries; run with python -m unittest discover -s tests."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import call, patch

import requests

from withings_sync import withings2


def response(payload=None, status=200):
    result = requests.Response()
    result.status_code = status
    result.url = withings2.GETMEAS_URL
    result._content = json.dumps(payload).encode()
    return result


class ApiRequestTests(unittest.TestCase):
    def setUp(self):
        post_patch = patch.object(withings2.requests, "post")
        sleep_patch = patch.object(withings2.time, "sleep")
        self.post = post_patch.start()
        self.sleep = sleep_patch.start()
        self.addCleanup(post_patch.stop)
        self.addCleanup(sleep_patch.stop)
        self.success = {"status": 0, "body": {"measuregrps": []}}

    def request(self, **kwargs):
        return withings2._api_request(withings2.GETMEAS_URL, {}, **kwargs)

    def test_success_has_timeout_and_no_sleep(self):
        self.post.return_value = response(self.success)
        self.assertEqual(self.request(), self.success)
        self.post.assert_called_once_with(withings2.GETMEAS_URL, {}, timeout=30)
        self.sleep.assert_not_called()

    def test_rate_limit_honors_server_wait(self):
        self.post.side_effect = [
            response({"status": 601, "body": {"wait_seconds": 76}}),
            response(self.success),
        ]
        self.assertEqual(self.request(), self.success)
        self.sleep.assert_called_once_with(76)

    def test_exhausted_rate_limit_does_not_sleep_after_last_attempt(self):
        self.post.return_value = response(
            {"status": 601, "error": "Too Many Requests", "body": {"wait_seconds": 76}}
        )
        with self.assertRaisesRegex(
            withings2.WithingsException, "status 601.*Too Many Requests.*3 attempts"
        ):
            self.request()
        self.assertEqual(self.post.call_count, 3)
        self.assertEqual(self.sleep.call_args_list, [call(76), call(76)])

    def test_permanent_http_errors_fail_immediately(self):
        for status in (400, 401, 403, 404):
            with self.subTest(status=status):
                self.post.reset_mock()
                self.post.return_value = response(status=status)
                with self.assertRaisesRegex(
                    withings2.WithingsException, str(status)
                ) as raised:
                    self.request()
                self.assertIsInstance(raised.exception.__cause__, requests.HTTPError)
                self.post.assert_called_once()
                self.sleep.assert_not_called()

    def test_transient_http_errors_are_retried(self):
        for status in (408, 429, 500, 502, 503, 504):
            with self.subTest(status=status):
                self.sleep.reset_mock()
                self.post.side_effect = [
                    response(status=status),
                    response(self.success),
                ]
                self.assertEqual(self.request(), self.success)
                self.sleep.assert_called_once_with(1.0)

    def test_connection_failure_preserves_cause_and_uses_backoff(self):
        error = requests.ConnectionError("connection unavailable")
        self.post.side_effect = error
        with self.assertRaisesRegex(
            withings2.WithingsException, "connection unavailable.*3 attempts"
        ) as raised:
            self.request()
        self.assertIs(raised.exception.__cause__, error)
        self.assertEqual(self.sleep.call_args_list, [call(1.0), call(2.0)])

    def test_invalid_json_is_retried(self):
        invalid = response()
        invalid._content = b"invalid JSON"
        self.post.side_effect = [invalid, response(self.success)]
        self.assertEqual(self.request(), self.success)
        self.sleep.assert_called_once_with(1.0)

    def test_rate_limit_with_zero_wait_retries(self):
        self.post.side_effect = [
            response({"status": 601, "body": {"wait_seconds": 0}}),
            response(self.success),
        ]
        self.assertEqual(self.request(), self.success)
        self.sleep.assert_called_once_with(0)

    def test_missing_or_invalid_wait_uses_backoff(self):
        for wait in (None, -1, "invalid", float("inf"), float("nan")):
            with self.subTest(wait=wait):
                self.sleep.reset_mock()
                self.post.side_effect = [
                    response({"status": 601, "body": {"wait_seconds": wait}}),
                    response(self.success),
                ]
                self.assertEqual(self.request(), self.success)
                self.sleep.assert_called_once_with(1.0)

    def test_api_authentication_error_is_not_retried(self):
        self.post.return_value = response({"status": 401, "error": "invalid token"})
        with self.assertRaisesRegex(
            withings2.WithingsException, "status 401.*invalid token"
        ):
            self.request()
        self.post.assert_called_once()
        self.sleep.assert_not_called()

    def test_one_attempt_never_sleeps(self):
        self.post.side_effect = requests.Timeout("timed out")
        with self.assertRaisesRegex(
            withings2.WithingsException, "timed out.*1 attempts"
        ):
            self.request(max_retries=1)
        self.sleep.assert_not_called()

    def test_invalid_attempt_count_does_not_send_request(self):
        with self.assertRaises(ValueError):
            self.request(max_retries=0)
        self.post.assert_not_called()

    def test_measurements_keep_raw_response(self):
        account = withings2.WithingsAccount.__new__(withings2.WithingsAccount)
        account.withings = SimpleNamespace(user_config={"access_token": "test"})
        self.post.return_value = response(self.success)
        self.assertEqual(account.get_measurements(1, 2), [])
        self.assertEqual(account.last_measurements_json, self.success)

    def test_height_failure_remains_nonfatal(self):
        account = withings2.WithingsAccount.__new__(withings2.WithingsAccount)
        account.withings = SimpleNamespace(user_config={"access_token": "test"})
        self.post.return_value = response(status=401)
        self.assertIsNone(account.get_height())


if __name__ == "__main__":
    unittest.main()
