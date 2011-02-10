# -*- coding: utf-8 -*-

import urllib
from hashlib import md5
from datetime import datetime

try:
    import json
except ImportError:
    import simplejson as json


class WithingsException(Exception):
    pass


class WithingsAPIError(WithingsException):
    DESCRIPTIONS = {
        100: 'The hash is missing, invalid, or does not match the provided email',
        247: 'The userid is absent, or incorrect',
        250: 'The userid and publickey do not match, or the user does not share its data',
        264: 'The email address provided is either unknown or invalid',
        286: 'No such subscription was found',  # ?
        293: 'The callback URL is either absent or incorrect',
        294: 'No such subscription could be deleted',
        304: 'The comment is either absent or incorrect',
        2555: 'An unknown error occured',
    }

    def __init__(self, status=2555):
        self.status = status
        self.message = self.DESCRIPTIONS.get(status, 'unknown status')


class Withings(object):
    BASE_URL = 'http://wbsapi.withings.net/'

    def magic_string(self):
        res = self.call('once', 'get')
        return res.get('once')

    def call(self, service, action, params=None):
        url = self.build_url(service, action, params)
        res = urllib.urlopen(url).read()
        try:
            res = json.loads(res)
        except ValueError:
            raise WithingsException('API does not return valid json response.')
        status = res.get('status')
        if (status != 0):
            raise WithingsAPIError(status)
        return res.get('body')

    def build_url(self, service, action, params=None):
        url = '%s%s?action=%s' % (Withings.BASE_URL, service, action)
        if params:
            if isinstance(params, dict):
                params = dict((k, v) for k, v in params.items() if v is not None)
                params = urllib.urlencode(params)
            url = '%s&%s' % (url, params)
        return url


class WithingsAccount(Withings):
    def __init__(self, email, password):
        self.email = email
        self.password = password

    def hash(self):
        md5hash = lambda s: md5(s).hexdigest()
        magic = self.magic_string()
        hash_base = '%s:%s:%s' % (self.email, md5hash(self.password), magic)
        return md5hash(hash_base)

    def getuserslist(self):
        """return users list(raw API response)"""
        params = {'email': self.email, 'hash': self.hash()}
        return self.call('account', 'getuserslist', params)

    def get_users(self):
        """return users list(list of WithingsUser object)"""
        res = self.getuserslist()
        # convert to user object
        return [WithingsUser.create(u) for u in res['users']]

    def get_user_by_shortname(self, shortname):
        for user in self.get_users():
            if user.shortname == shortname:
                return user
        return None


class WithingsUser(Withings):
    @staticmethod
    def create(userdata):
        user = WithingsUser(userdata.get('id'), userdata.get('publickey'))
        user.set_attributes(userdata)
        return user

    def __init__(self, id, publickey):
        self.id = id
        self.publickey = publickey
        self._valid_attrs = ['fatmethod', 'firstname', 'lastname', 'ispublic',
                             'birthdate', 'gender', 'shortname']

    def __getattr__(self, name):
        if name in self.__dict__['_valid_attrs']:
            if name not in self.__dict__:
                self.getbyuserid()
        if name in self.__dict__:
            return self.__dict__[name]
        raise AttributeError

    def __str__(self):
        return '%s: %s' % (self.id, self.fullname())

    def set_attributes(self, userdata):
        for a in self._valid_attrs:
            v = userdata.get(a)
            if v is not None:
                setattr(self, a, v)

    def getbyuserid(self):
        res = self.call('user', 'getbyuserid', {'userid': self.id, 'publickey': self.publickey})
        self.set_attributes(res['users'].pop(0))
        return res

    def getmeasure(self, *args, **kwargs):
        defaults = {'userid': self.id, 'publickey': self.publickey}
        defaults.update(kwargs)
        return self.call('measure', 'getmeas', defaults)

    def get_measure_groups(self, *args, **kwargs):
        res = self.getmeasure(*args, **kwargs)
        return [WithingsMeasureGroup(g) for g in res['measuregrps']]

    def fullname(self):
        return '%s %s' % (self.firstname, self.lastname)

    def isMale(self):
        return self.gender == 0

    def isFemele(self):
        return self.gender == 1


class WithingsMeasureGroup(object):
    def __init__(self, measuregrp):
        self._raw_data = measuregrp
        self.id = measuregrp.get('grpid')
        self.attrib = measuregrp.get('attrib')
        self.date = measuregrp.get('date')
        self.category = measuregrp.get('category')
        self.measures = [WithingsMeasure(m) for m in measuregrp['measures']]

    def __iter__(self):
        for measure in self.measures:
            yield measure

    def __len__(self):
        return len(self.measures)

    def get_datetime(self):
        return datetime.fromtimestamp(self.date)

    def get_weight(self):
        """convinient function to get weight"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_WEIGHT:
                return measure.get_value()
        return None

    def get_fat_ratio(self):
        """convinient function to get fat ratio"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_FAT_RATIO:
                return measure.get_value()
        return None


class WithingsMeasure(object):
    TYPE_WEIGHT = 1
    TYPE_HEIGHT = 4
    TYPE_FAT_FREE_MASS = 5
    TYPE_FAT_RATIO = 6
    TYPE_FAT_MASS_WEIGHT = 8

    def __init__(self, measure):
        self._raw_data = measure
        self.value = measure.get('value')
        self.type = measure.get('type')
        self.unit = measure.get('unit')

    def __str__(self):
        type_s = 'unknown'
        unit_s = ''
        if (self.type == self.TYPE_WEIGHT):
            type_s = 'Weight'
            unit_s = 'kg'
        elif (self.type == self.TYPE_HEIGHT):
            type_s = 'Height'
            unit_s = 'meter'
        elif (self.type == self.TYPE_FAT_FREE_MASS):
            type_s = 'Fat Free Mass'
            unit_s = 'kg'
        elif (self.type == self.TYPE_FAT_RATIO):
            type_s = 'Fat Ratio'
            unit_s = '%'
        elif (self.type == self.TYPE_FAT_MASS_WEIGHT):
            type_s = 'Fat Mass Weight'
            unit_s = 'kg'
        return '%s: %s %s' % (type_s, self.get_value(), unit_s)

    def get_value(self):
        return self.value * pow(10, self.unit)

