"""This module handles the Garmin connectivity."""

import logging
import os
import tempfile

from garminconnect import Garmin

log = logging.getLogger("garmin")

HOME = os.getenv("HOME", ".")
GARMIN_SESSION = os.path.abspath(
    os.path.expanduser(
        os.getenv("GARMIN_SESSION", os.path.join(HOME, ".garmin_session"))
    )
)


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

        # Log helpful message if using new config folder and file doesn't exist
        if config_folder and not os.path.exists(self.session_path):
            home = os.getenv("HOME", ".")
            legacy_path = os.path.abspath(
                os.path.expanduser(os.path.join(home, ".garmin_session"))
            )
            if os.path.exists(legacy_path):
                log.info(f"Using new config folder: {self.session_path}")
                log.info(
                    f"If you want to use existing session, copy from: {legacy_path}"
                )

    def login(self, email=None, password=None):
        """Login to Garmin Connect."""
        if not email or not password:
            raise APIException(
                "No valid session found and no credentials provided. "
                "For MFA accounts: "
                "1) Authenticate once using Garmin Connect mobile app or web interface, "
                "2) Locate the session/token file in your config directory, "
                "3) Ensure the file is accessible at the path specified by "
                "GARMIN_SESSION environment variable."
            )

        # Ensure parent directory exists before attempting login/token save
        session_dir = os.path.dirname(self.session_path)
        if session_dir:
            os.makedirs(session_dir, exist_ok=True)

        # Check write permissions — garminconnect silently suppresses token
        # save failures, so without this warning the user would re-authenticate
        # on every run without knowing why
        if session_dir and not os.access(session_dir, os.W_OK):
            log.warning(
                f"Cannot write to session directory: {session_dir}. "
                f"Session tokens will not be persisted between runs."
            )

        try:
            self.client = Garmin(email, password)
            self.client.login(self.session_path)
            log.info("Garmin authentication successful")
        except Exception as ex:
            raise APIException(
                f"Authentication failure: {ex}. "
                f"Ensure your credentials are correct. "
                f"For MFA accounts, you may need to authenticate interactively first."
            )

        # Verify token was actually persisted — garminconnect uses
        # contextlib.suppress(Exception) on dump(), so a silent failure
        # means every future run hits Garmin SSO again
        if not os.path.exists(self.session_path):
            log.warning(
                f"Garmin session token was not saved to {self.session_path}. "
                f"Check path permissions. Without a saved session, "
                f"credentials will be required on every run."
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
