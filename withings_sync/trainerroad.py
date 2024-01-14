import requests
import json
import logging

from lxml import etree
from io import StringIO

logger = logging.getLogger(__name__)


class TrainerRoad:
    _ftp = 'Ftp'
    _weight = 'Weight'
    _units_metric = 'kmh'
    _units_imperial = 'mph'
    _input_data_names = (_ftp, _weight, 'Marketing', 'DateOfBirth')
    _select_data_names = ('TimeZoneId', 'IsPrivate',
                          'Units', 'IsVirtualPowerEnabled',
                          'GenderId', 'GenderCustomText', 'Locale')
    _numerical_verify = (_ftp, _weight)
    _string_verify = _select_data_names + ('Marketing',)
    _login_url = 'https://www.trainerroad.com/app/login'
    _logout_url = 'https://www.trainerroad.com/app/logout'
    _rider_url = 'https://www.trainerroad.com/app/profile/rider-information'
    _download_tcx_url = 'http://www.trainerroad.com/cycling/rides/download'
    _workouts_url = 'https://api.trainerroad.com/api/careerworkouts'
    _rvt = '__RequestVerificationToken'

    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._session = None

    def connect(self):
        self._session = requests.Session()
        self._session.auth = (self._username, self._password)

        data = {'Username': self._username,
                'Password': self._password}

        r = self._session.post(self._login_url, data=data,
                               allow_redirects=False)

        if r.status_code not in [200, 302]:
            # There was an error
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


    def _parse_value(self, tree, name):
        rtn = tree.xpath('//form//input[@name="{}"]/@value'.format(name))
        if not rtn:
            raise RuntimeError('Input {} not found in form'.format(name))
        return rtn[0]

    def _parse_name(self, tree, name):
        rtn = tree.xpath('//form//select[@name="{}"]//option'
                         '[@selected="selected"]/@value'.format(name))

        if not rtn:
            if name == 'GenderCustomText':
                return ""
            else:
                raise RuntimeError('Input {} not found in form'.format(name))

        return rtn[0]

    def _get(self, url):
        if self._session is None:
            raise RuntimeError('Not Connected')

        r = self._session.get(url)

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
        r = self._get(self._rider_url)

        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(r.text), parser)

        token = self._parse_value(tree, self._rvt)

        input_data = {}
        for key in self._input_data_names:
            input_data[key] = self._parse_value(tree, key)

        select_data = {}
        for key in self._select_data_names:
            select_data[key] = self._parse_name(tree, key)

        return (dict(**input_data, **select_data), token)

    def _write_profile(self, new_values):
        # Read values
        data, token = self._read_profile()

        logger.info("Read profile values {}".format(data))
        logger.debug("Token = {}".format(token))

        # Update values with new_values
        for key, value in new_values.items():
            if key not in data:
                raise ValueError("Key \"{}\" is not in profile form"
                                 .format(key))
            if key == self._weight and data['Units'] == self._units_imperial:
                value = round(value/0.45359237, 1)
                logger.debug("Converting Weight to lbs {}".format(value))

            # ONLY if GenderId == 4 ("Prefer to self-describe")
            # add GenderCustomText
            if key == "GenderCustomText" and data["GenderId" ] != "4":
                continue

            data[key] = str(value)

        logger.info("New profile values {}".format(data))

        # Now post the form
        token = {self._rvt: token}
        self._post(self._rider_url, data=dict(**data, **token))

        # Now re-read to check
        _data, token = self._read_profile()

        logger.info("Read profile values (verification) {}".format(_data))

        for key in self._numerical_verify:
            logger.debug('Numerically verifying key "{}" "{}" with "{}"'
                         .format(key, data[key], _data[key]))
            if float(data[key]) != float(_data[key]):
                raise RuntimeError('Failed to verify numerical key {}'
                                   .format(key))
        for key in self._string_verify:
            logger.debug('String verifying key "{}" "{}" with "{}"'
                         .format(key, data[key], _data[key]))
            if data[key] != _data[key]:
                raise RuntimeError('Failed to verify string key {}'.format(key))

        return

    @property
    def ftp(self):
        values, token = self._read_profile()
        return values[self._ftp]

    @ftp.setter
    def ftp(self, value):
        self._write_profile({self._ftp: value})

    @property
    def weight(self):
        values, token = self._read_profile()
        return values[self._weight]

    @weight.setter
    def weight(self, value):
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
