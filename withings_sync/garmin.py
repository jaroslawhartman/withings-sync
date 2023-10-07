"""This module handles the Garmin connectivity."""
import logging
import garth
import os
import io

log = logging.getLogger("garmin")


HOME = os.getenv('HOME', '.')
GARMIN_SESSION = os.getenv('GARMIN_SESSION', HOME + '/.garmin_session')


class LoginSucceeded(Exception):
    """Used to raise on LoginSucceeded"""


class LoginFailed(Exception):
    """Used to raise on LoginFailed"""


class APIException(Exception):
    """Used to raise on APIException"""


class GarminConnect:
    """Main GarminConnect class"""

    def __init__(self) -> None:
        self.client = garth.Client()

    def login(self, email=None, password=None):
        logged_in = False
        if os.path.exists(GARMIN_SESSION):
            self.client.load(GARMIN_SESSION)
            try:
                self.client.username
                logged_in = True
            except Exception:
                pass

        if not logged_in:
            try:
                self.client.login(email, password)
                self.client.dump(GARMIN_SESSION)
            except Exception as ex:
                raise APIException("Authentication failure: {}. Did you enter correct credentials?".format(ex))


    def upload_file(self, ffile):
        """upload fit file to Garmin connect"""
        # Convert the fitfile to a in-memory file for upload
        fit_file = io.BytesIO(ffile.getvalue())
        fit_file.name = 'withings.fit'
        self.client.upload(fit_file)
        return True
