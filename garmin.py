# -*- coding: utf-8 -*-

import urllib2
import urllib
import datetime


class LoginSucceeded(Exception):
    pass


class LoginFailed(Exception):
    pass


class GarminConnect(object):
    LOGIN_URL = 'https://connect.garmin.com/signin'
    WEIGHT_INPUT_URL = 'http://connect.garmin.com/proxy/user-service-1.0/json/weight'

    def __init__(self):
        self.opener = self.create_opener()

    def create_opener(self):
        this = self
        class _HTTPRedirectHandler(urllib2.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                if req.get_full_url() == this.LOGIN_URL:
                    raise LoginSucceeded
                return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        return urllib2.build_opener(_HTTPRedirectHandler, urllib2.HTTPCookieProcessor())

    def login(self, username, password):
        # prepare session cookies or so.
        # you cannot login without access any Garmin Connect page.
        self.opener.open(self.LOGIN_URL)

        params = {'login:loginUsernameField': username,
                  'login:password': password,
                  'login': 'login',
                  'login:signInButton': 'Sign In',
                  'javax.faces.ViewState': 'j_id1'}
        try:
            self.opener.open(self.LOGIN_URL, urllib.urlencode(params))
        except LoginSucceeded:
            return True
        raise LoginFailed('invalid username or password')

    def post_weight(self, date, value):
        if isinstance(date, (datetime.datetime, datetime.date)):
            date = date.strftime('%Y-%m-%d')
        params = {'date': date, 'value': value, 'returnProvidedValues': 'true'}
        r = self.opener.open(self.WEIGHT_INPUT_URL, urllib.urlencode(params))
        return r.code == 200

