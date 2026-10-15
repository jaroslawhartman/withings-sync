"""OAuth regression tests; run with python -m unittest discover -s tests."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from withings_sync import withings2


APP_CONFIG = {
    "client_id": "test-client",
    "consumer_secret": "test-secret",
    "callback_url": "https://example.invalid/callback",
}
USER_CONFIG = {
    "access_token": "old-access",
    "refresh_token": "old-refresh",
    "userid": 123,
    "authentification_code": "test-code",
    "last_sync": 456,
    "last_sync_tr": 789,
}
NEW_TOKENS = {
    "access_token": "new-access",
    "refresh_token": "new-refresh",
    "userid": 123,
}
TOKEN_METHODS = ("get_accesstoken", "refresh_accesstoken")


def response(payload=None, status=200):
    result = requests.Response()
    result.status_code = status
    result.url = withings2.TOKEN_URL
    result._content = json.dumps(payload).encode()
    return result


class OAuthTokenTests(unittest.TestCase):
    def setUp(self):
        self.account = withings2.WithingsOAuth2.__new__(withings2.WithingsOAuth2)
        self.account.app_config = copy.deepcopy(APP_CONFIG)
        post_patch = patch.object(withings2.requests, "post")
        sleep_patch = patch.object(withings2.time, "sleep")
        self.post = post_patch.start()
        self.sleep = sleep_patch.start()
        self.addCleanup(post_patch.stop)
        self.addCleanup(sleep_patch.stop)

    def reset_request(self):
        self.account.user_config = copy.deepcopy(USER_CONFIG)
        self.post.reset_mock(return_value=True, side_effect=True)
        self.sleep.reset_mock()

    def assert_rejected(self, payload, message=None):
        for method in TOKEN_METHODS:
            with self.subTest(method=method, payload=payload):
                self.reset_request()
                self.post.return_value = response(payload)
                with self.assertRaises(withings2.WithingsException) as raised:
                    getattr(self.account, method)()
                if message is not None:
                    self.assertIn(message, str(raised.exception))
                self.assertEqual(self.account.user_config, USER_CONFIG)
                self.post.assert_called_once()
                self.sleep.assert_not_called()

    def test_success_updates_tokens_and_preserves_other_fields(self):
        for method, grant in zip(
            TOKEN_METHODS, ("authorization_code", "refresh_token")
        ):
            with self.subTest(method=method):
                self.reset_request()
                self.post.return_value = response({"status": 0, "body": NEW_TOKENS})
                getattr(self.account, method)()
                self.assertEqual(self.account.user_config, USER_CONFIG | NEW_TOKENS)
                params = {
                    "action": "requesttoken",
                    "grant_type": grant,
                    "client_id": APP_CONFIG["client_id"],
                    "client_secret": APP_CONFIG["consumer_secret"],
                }
                if grant == "authorization_code":
                    params.update(
                        code=USER_CONFIG["authentification_code"],
                        redirect_uri=APP_CONFIG["callback_url"],
                    )
                else:
                    params["refresh_token"] = USER_CONFIG["refresh_token"]
                self.post.assert_called_once_with(
                    withings2.TOKEN_URL, params, timeout=30
                )
                self.sleep.assert_not_called()

    def test_api_errors_preserve_tokens(self):
        for payload in ({"status": 503}, {"status": 503, "body": {}}):
            self.assert_rejected(payload, "status 503")

    def test_nested_error_message_is_retained(self):
        error = "Invalid Params: invalid refresh_token"
        self.assert_rejected({"status": 503, "body": {"error": error}}, error)

    def test_top_level_error_message_takes_precedence(self):
        payload = {
            "status": 601,
            "error": "Too Many Requests",
            "body": {"error": "nested error", "wait_seconds": 76},
        }
        self.assert_rejected(payload, "Too Many Requests")

    def test_empty_or_invalid_top_level_error_uses_nested_error(self):
        for error in (None, "", [], 42):
            self.assert_rejected(
                {"status": 503, "error": error, "body": {"error": "nested error"}},
                "nested error",
            )

    def test_missing_or_invalid_error_message_uses_fallback(self):
        for body in (None, [], {"error": None}, {"error": []}, {"error": ""}):
            self.assert_rejected(
                {"status": 503, "error": None, "body": body},
                "no error message provided",
            )

    def test_success_requires_a_body_object(self):
        self.assert_rejected({"status": 0})
        for body in (None, {}, [], "", "not an object", 42, True):
            self.assert_rejected({"status": 0, "body": body})

    def test_success_requires_complete_token_fields(self):
        for field in NEW_TOKENS:
            body = NEW_TOKENS.copy()
            del body[field]
            self.assert_rejected({"status": 0, "body": body}, field)
        for field in ("access_token", "refresh_token"):
            for value in (None, "", 42, False, []):
                body = NEW_TOKENS | {field: value}
                self.assert_rejected({"status": 0, "body": body}, field)
        self.assert_rejected(
            {"status": 0, "body": NEW_TOKENS | {"userid": None}}, "userid"
        )

    def test_json_response_must_be_an_object(self):
        for payload in (None, [], "not an object", 42, True):
            self.assert_rejected(payload)

    def test_missing_status_is_rejected(self):
        self.assert_rejected({"body": NEW_TOKENS})

    def test_invalid_json_preserves_tokens_and_cause(self):
        for method in TOKEN_METHODS:
            with self.subTest(method=method):
                self.reset_request()
                invalid = response()
                invalid._content = b"invalid JSON"
                self.post.return_value = invalid
                with self.assertRaises(withings2.WithingsException) as raised:
                    getattr(self.account, method)()
                self.assertIsInstance(raised.exception.__cause__, ValueError)
                self.assertEqual(self.account.user_config, USER_CONFIG)
                self.post.assert_called_once()
                self.sleep.assert_not_called()

    def test_http_errors_preserve_tokens_and_cause_without_retrying(self):
        for method in TOKEN_METHODS:
            for status in (400, 401, 429, 500, 503):
                with self.subTest(method=method, status=status):
                    self.reset_request()
                    self.post.return_value = response(status=status)
                    with self.assertRaises(withings2.WithingsException) as raised:
                        getattr(self.account, method)()
                    self.assertIsInstance(
                        raised.exception.__cause__, requests.HTTPError
                    )
                    self.assertEqual(self.account.user_config, USER_CONFIG)
                    self.post.assert_called_once()
                    self.sleep.assert_not_called()

    def test_network_errors_preserve_tokens_and_cause_without_retrying(self):
        for method in TOKEN_METHODS:
            for error_type in (requests.ConnectionError, requests.Timeout):
                with self.subTest(method=method, error_type=error_type):
                    self.reset_request()
                    error = error_type("request failed")
                    self.post.side_effect = error
                    with self.assertRaises(withings2.WithingsException) as raised:
                        getattr(self.account, method)()
                    self.assertIs(raised.exception.__cause__, error)
                    self.assertEqual(self.account.user_config, USER_CONFIG)
                    self.post.assert_called_once()
                    self.sleep.assert_not_called()


class OAuthPersistenceTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        (self.folder / "withings_app.json").write_text(
            json.dumps(APP_CONFIG), encoding="utf8"
        )
        self.user_path = self.folder / ".withings_user.json"
        self.original_bytes = json.dumps(USER_CONFIG, indent=2).encode()
        self.user_path.write_bytes(self.original_bytes)
        post_patch = patch.object(withings2.requests, "post")
        input_patch = patch(
            "builtins.input", side_effect=AssertionError("Unexpected prompt")
        )
        self.post = post_patch.start()
        self.input = input_patch.start()
        self.addCleanup(post_patch.stop)
        self.addCleanup(input_patch.stop)

    def test_failed_refresh_leaves_config_file_byte_for_byte_unchanged(self):
        for payload in (
            {"status": 503, "body": {"error": "invalid refresh_token"}},
            {"status": 0},
            {"status": 0, "body": None},
            {"status": 0, "body": {}},
            {"status": 0, "body": {"access_token": "new-access"}},
        ):
            with self.subTest(payload=payload):
                self.post.reset_mock()
                self.post.return_value = response(payload)
                with patch.object(
                    withings2.WithingsConfig, "write", autospec=True
                ) as write:
                    with self.assertRaises(withings2.WithingsException):
                        withings2.WithingsOAuth2(config_folder=str(self.folder))
                    write.assert_not_called()
                self.assertEqual(self.user_path.read_bytes(), self.original_bytes)
                self.post.assert_called_once()
                self.input.assert_not_called()

    def test_successful_refresh_saves_new_tokens_and_preserves_other_fields(self):
        self.post.return_value = response({"status": 0, "body": NEW_TOKENS})
        account = withings2.WithingsOAuth2(config_folder=str(self.folder))
        expected = USER_CONFIG | NEW_TOKENS
        self.assertEqual(account.user_config, expected)
        self.assertEqual(json.loads(self.user_path.read_bytes()), expected)
        self.post.assert_called_once()
        self.input.assert_not_called()


if __name__ == "__main__":
    unittest.main()
