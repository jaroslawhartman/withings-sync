"""This module handles the Garmin connectivity."""

import logging
import os
import tempfile
from pathlib import Path

from garminconnect import Garmin

log = logging.getLogger("garmin")

HOME = os.getenv("HOME", ".")
GARMIN_SESSION = os.path.abspath(
    os.path.expanduser(
        os.getenv("GARMIN_SESSION", os.path.join(HOME, ".garmin_session"))
    )
)

TOKENSTORE_FILENAME = "garmin_tokens.json"


class LoginFailed(Exception):
    """Raised when login fails."""


class APIException(Exception):
    """Raised for API exceptions."""


class GarminConnect:
    """Main GarminConnect class."""

    def __init__(self, config_folder=None) -> None:
        self.client = None
        self.config_folder = config_folder

        if config_folder:
            self.session_path = os.path.join(config_folder, ".garmin_session")
        else:
            self.session_path = GARMIN_SESSION

        # Log helpful message if using new config folder and no tokenstore exists yet
        tokenstore_path = self._normalize_tokenstore_path()
        if config_folder and not os.path.exists(tokenstore_path):
            home = os.getenv("HOME", ".")
            legacy_path = os.path.abspath(
                os.path.expanduser(os.path.join(home, ".garmin_session"))
            )
            if os.path.exists(legacy_path):
                log.info(
                    "Existing garth session files cannot be reused directly. "
                    "After one fresh login, new Garmin tokens will be stored at: %s",
                    tokenstore_path,
                )

    def _normalize_tokenstore_path(self) -> str:
        """Map legacy file-style paths to safe tokenstore paths.

        python-garminconnect's client.load()/dump() append garmin_tokens.json
        when the path is a directory or doesn't end in .json. If a legacy garth
        session FILE exists at the configured path, passing it through unchanged
        causes a file-inside-file collision that silently defeats token persistence.
        """
        path = Path(self.session_path).expanduser()

        # Preserve explicit upstream-native .json file paths
        if path.suffix == ".json":
            return str(path)

        # Preserve explicit directory paths
        if path.exists() and path.is_dir():
            return str(path)

        # Map legacy file-style paths (e.g. ~/.garmin_session) to a .json file
        # to avoid collision with old garth session files
        return f"{path}.json"

    def _token_artifact_path(self, tokenstore_path: str) -> str:
        """Determine where garminconnect will actually write the token file.

        Mirrors the logic in garminconnect's client.load()/dump():
        if the path ends in .json it's used directly, otherwise
        garmin_tokens.json is appended inside the directory.
        """
        if tokenstore_path.endswith(".json"):
            return tokenstore_path
        return os.path.join(tokenstore_path, TOKENSTORE_FILENAME)

    def login(self, email=None, password=None):
        """Login to Garmin Connect.

        Attempts tokenstore-first login: if saved tokens exist and are still
        valid, credentials are not required. Credential-based login is only
        attempted when token restore fails.
        """
        tokenstore_path = self._normalize_tokenstore_path()
        token_artifact = self._token_artifact_path(tokenstore_path)

        # Ensure parent directory exists before attempting login/token save
        write_target = (
            os.path.dirname(tokenstore_path)
            if tokenstore_path.endswith(".json")
            else tokenstore_path
        )
        if write_target:
            os.makedirs(write_target, exist_ok=True)

        # Check write permissions — garminconnect silently suppresses token
        # save failures via contextlib.suppress(Exception), so without this
        # warning the user would re-authenticate on every run with no indication
        if write_target and not os.access(write_target, os.W_OK):
            log.warning(
                "Cannot write to Garmin tokenstore location: %s. "
                "Tokens may not persist between runs.",
                write_target,
            )

        try:
            self.client = Garmin(email, password, prompt_mfa=lambda: input("MFA code: "))
            self.client.login(tokenstore_path)
            log.info("Garmin authentication successful")
        except Exception as ex:
            if not email or not password:
                raise APIException(
                    "No valid saved Garmin tokenstore was found and no credentials "
                    "were provided. If you upgraded from garth, the old "
                    ".garmin_session file cannot be reused directly; perform one "
                    "fresh login to create a new python-garminconnect tokenstore."
                ) from ex

            raise APIException(
                f"Authentication failure: {ex}. "
                "Ensure your credentials are correct. "
                "For MFA accounts, you may need to authenticate interactively first."
            ) from ex

        # Verify token was actually persisted — garminconnect uses
        # contextlib.suppress(Exception) on dump(), so a silent failure
        # means every future run hits Garmin SSO again
        if not os.path.exists(token_artifact):
            log.warning(
                "Garmin tokens were not saved to %s. Without persisted tokens, "
                "future runs may require re-authentication.",
                token_artifact,
            )

    def upload_file(self, ffile):
        """Upload fit file to Garmin Connect."""
        # python-garminconnect only accepts file paths, not file-like objects
        with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmp:
            tmp.write(ffile.getvalue())
            tmp_path = tmp.name
        try:
            self.client.upload_activity(tmp_path)
        finally:
            os.unlink(tmp_path)
        return True
