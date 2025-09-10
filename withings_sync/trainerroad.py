import requests
import json
import logging

logger = logging.getLogger(__name__)


class TrainerRoad:
    _ftp = 'ftp'
    _weight = 'weightKg'
    _units_metric = 'kmh'
    _units_imperial = 'mph'
    _numerical_verify = (_ftp, _weight)
    _login_url = 'https://www.trainerroad.com/app/login'
    _logout_url = 'https://www.trainerroad.com/app/logout'
    _profile_api_url = 'https://www.trainerroad.com/app/api/profile/rider-information'
    _download_tcx_url = 'http://www.trainerroad.com/cycling/rides/download'
    _workouts_url = 'https://api.trainerroad.com/api/careerworkouts'

    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._session = None

    def connect(self):
        self._session = requests.Session()
        
        data = {'Username': self._username,
                'Password': self._password}

        r = self._session.post(self._login_url, data=data,
                               allow_redirects=False)

        if r.status_code not in [200, 302]:
            raise RuntimeError("Error loging in to TrainerRoad (Code {})"
                               .format(r.status_code))

        logger.info('Logged into TrainerRoad as "{}"'.format(self._username))

    def disconnect(self):
        r = self._session.get(self._logout_url, allow_redirects=False)
        if r.status_code not in [200, 302]:
            raise RuntimeError("Error loging out of TrainerRoad (Code {})"
                               .format(r.status_code))

        self._session = None
        logger.info('Logged out of TrainerRoad as "{}"'.format(self._username))

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.disconnect()



    def _get(self, url):
        if self._session is None:
            raise RuntimeError('Not Connected')

        # Add browser-like headers for API calls (camelCase JSON format)
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.trainerroad.com/app/profile/rider-information',
            'trainerroad-jsonformat': 'camel-case',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0'
        }

        r = self._session.get(url, headers=headers)

        if r.status_code != 200:
            raise RuntimeError("Error getting info from TrainerRoad (Code {})"
                               .format(r.status_code))

        return r

    def _post(self, url, data):
        if self._session is None:
            raise RuntimeError('Not Connected')

        r = self._session.post(url, data)

        if r.status_code != 200:
            raise RuntimeError("Error posting info to TrainerRoad (Code {})"
                               .format(r.status_code))

        return r

    def _read_profile(self):
        """Read profile data from TrainerRoad JSON API"""
        r = self._get(self._profile_api_url)
        
        if r.status_code != 200:
            raise RuntimeError("Error getting profile from TrainerRoad (Code {})"
                               .format(r.status_code))
        
        profile_data = r.json()
        logger.debug("Profile API response: {}".format(json.dumps(profile_data, indent=2)))
        
        return profile_data

    def _write_profile(self, new_values):
        """Write profile data to TrainerRoad JSON API"""
        # Read current values
        data = self._read_profile()
        original_data = data.copy()

        logger.info("Current profile values: Weight={}, FTP={}".format(
            data.get(self._weight), data.get(self._ftp)))

        # Update values with new_values
        for key, value in new_values.items():
            if key == self._weight and data.get('Units') == self._units_imperial:
                value = round(value/0.45359237, 1)
                logger.debug("Converting Weight to lbs {}".format(value))
            
            data[key] = value

        logger.info("Updating profile: Weight={}, FTP={}".format(
            data.get(self._weight), data.get(self._ftp)))

        # Send PUT request with JSON data (exact browser headers)
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Origin': 'https://www.trainerroad.com',
            'Referer': 'https://www.trainerroad.com/app/profile/rider-information',
            'trainerroad-jsonformat': 'camel-case',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0'
        }
        r = self._session.put(self._profile_api_url, json=data, headers=headers)

        logger.debug("PUT request status: {}, response: {}".format(r.status_code, r.text[:200]))
        
        if r.status_code not in [200, 204]:
            raise RuntimeError("Error updating TrainerRoad profile (Code {})".format(r.status_code))

        # Verify the changes
        updated_data = self._read_profile()
        logger.info("Profile updated successfully: Weight={}, FTP={}".format(
            updated_data.get(self._weight), updated_data.get(self._ftp)))

        # Verify numerical fields
        for key in self._numerical_verify:
            if key in new_values:
                expected = float(new_values[key])
                if key == self._weight and original_data.get('Units') == self._units_imperial:
                    expected = round(expected/0.45359237, 1)
                actual = float(updated_data.get(key, 0))
                if abs(expected - actual) > 0.1:  # Allow small rounding differences
                    raise RuntimeError('Failed to verify numerical key {}: expected {}, got {}'
                                       .format(key, expected, actual))

        return

    @property
    def ftp(self):
        """Get current FTP value from TrainerRoad"""
        values = self._read_profile()
        return values.get(self._ftp)

    @ftp.setter
    def ftp(self, value):
        """Set FTP value in TrainerRoad"""
        self._write_profile({self._ftp: value})

    @property
    def weight(self):
        """Get current weight value from TrainerRoad"""
        values = self._read_profile()
        return values.get(self._weight)

    @weight.setter
    def weight(self, value):
        """Set weight value in TrainerRoad"""
        self._write_profile({self._weight: value})

    def download_tcx(self, id):
        res = self._session.get('{}/{}'.format(self._download_tcx_url, str(id)))
        if res.status_code != 200:
            raise RuntimeError("Unable to download (code = {})"
                               .format(res.status_code))

        return res.text

    def get_workouts(self):
        res = self._session.get(self._workouts_url)
        if res.status_code != 200:
            raise RuntimeError("Unable to download (code = {})"
                               .format(res.status_code))

        data = json.loads(res.text)
        logger.debug(json.dumps(data, indent=4, sort_keys=True))

        logger.info('Recieved info on {} workouts'.format(len(data)))

        return data

    def get_workout(self, guid):
        res = self._session.get(self._workout_url
                                + '?guid={}'.format(str(guid)))

        if res.status_code != 200:
            raise RuntimeError('Unable to get workout "{}" (Code = {})'
                               .format(guid, res.status_code))

        data = json.loads(res.text)
        logger.debug(json.dumps(data, indent=4, sort_keys=True))

        return data
