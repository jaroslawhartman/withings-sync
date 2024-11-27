"""This module handles the Garmin connectivity."""

import io
import logging
import os

import garth
# Temporary fix until Garth project merges https://github.com/matin/garth/issues/73
garth.http.USER_AGENT = {"User-Agent": ("GCM-iOS-5.7.2.1")}

log = logging.getLogger("garmin")

HOME = os.getenv("HOME", ".")
GARMIN_SESSION = os.getenv('GARMIN_SESSION', os.path.join(HOME, ".garmin_session"))


class LoginSucceeded(Exception):
    """Raised when login succeeds."""


class LoginFailed(Exception):
    """Raised when login fails."""


class APIException(Exception):
    """Raised for API exceptions."""


class GarminConnect:
    """Main GarminConnect class."""

    def __init__(self) -> None:
        self.client = garth.Client()

    def login(self, email=None, password=None):
        if os.path.exists(GARMIN_SESSION):
            self.client.load(GARMIN_SESSION)
            if hasattr(self.client, "username"):
                return

        try:
            self.client.login(email, password)
            self.client.dump(GARMIN_SESSION)
        except Exception as ex:
            raise APIException(
                f"Authentication failure: {ex}. Did you enter correct credentials?"
            )

    def upload_file(self, ffile):
        """Upload fit file to Garmin Connect."""
        fit_file = io.BytesIO(ffile.getvalue())
        fit_file.name = "withings.fit"
        self.client.upload(fit_file)
        return True
