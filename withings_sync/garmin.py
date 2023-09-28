"""This module handles the Garmin connectivity."""
import logging
import cloudscraper
import garth


log = logging.getLogger("garmin")


class LoginSucceeded(Exception):
    """Used to raise on LoginSucceeded"""


class LoginFailed(Exception):
    """Used to raise on LoginFailed"""


class APIException(Exception):
    """Used to raise on APIException"""


class GarminConnect:
    """Main GarminConnect class"""

    UPLOAD_URL = "https://connect.garmin.com/upload-service/upload/.fit"

    # From https://github.com/cpfair/tapiriik
    @staticmethod
    def get_session(email=None, password=None):
        """tapiriik get_session code"""
        session = cloudscraper.CloudScraper()

        try:
            garth.login(email, password)
        except Exception as ex:
            raise APIException("Authentication failure: {}. Did you enter correct credentials?".format(ex))

        session.headers.update({'NK': 'NT', 'authorization': garth.client.oauth2_token.__str__(), 'di-backend': 'connectapi.garmin.com'})
        return session

    @staticmethod
    def login(username, password):
        """login to Garmin"""
        return GarminConnect.get_session(email=username, password=password)

    def upload_file(self, ffile, session):
        """upload fit file to Garmin connect"""
        files = {"data": ("withings.fit", ffile)}
        res = session.post(self.UPLOAD_URL, files=files, headers={"nk": "NT"})
        try:
            resp = res.json()
            if "detailedImportResult" not in resp:
                raise KeyError
        except (ValueError, KeyError):
            if res.status_code == 204:  # HTTP result 204 - 'no content'
                log.error("No data to upload, try to use --fromdate and --todate")
            else:
                log.error("Bad response during GC upload: %s", res.status_code)

        return res.status_code in [200, 201, 204]
