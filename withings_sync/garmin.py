"""This module handles the Garmin connectivity."""
import logging
import garth
import os

log = logging.getLogger("garmin")


class LoginSucceeded(Exception):
    """Used to raise on LoginSucceeded"""


class LoginFailed(Exception):
    """Used to raise on LoginFailed"""


class APIException(Exception):
    """Used to raise on APIException"""


class GarminConnect:
    """Main GarminConnect class"""

    @staticmethod
    def get_session(email=None, password=None):
        logged_in = False
        if os.path.exists('./garmin_session'):
            garth.resume('./garmin_session')
            try:
                garth.client.username
                logged_in = True
            except Exception:
                pass

        if not logged_in:
            try:
                garth.login(email, password)
                garth.save('./garmin_session')
            except Exception as ex:
                raise APIException("Authentication failure: {}. Did you enter correct credentials?".format(ex))


    @staticmethod
    def login(username, password):
        """login to Garmin"""
        return GarminConnect.get_session(email=username, password=password)

    def upload_file(self, ffile):
        """upload fit file to Garmin connect"""
        files = {"data": ("withings.fit", ffile)}
        res = garth.client.post('connect', '/upload-service/upload/.fit', files=files, api=True, headers={'di-backend': 'connectapi.garmin.com'})
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
