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
    UPLOAD_URL = 'http://connect.garmin.com/proxy/upload-service-1.1/json/upload/.fit'
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

    def upload_file(self, f):
        # accept file object or string
        if isinstance(f, file):
            f.seek(0)
            fbody = f.read()
        else:
            fbody = f

        boundary = '----withingsgarmin'
        req = urllib2.Request(self.UPLOAD_URL)
        req.add_header('Content-Type', 'multipart/form-data; boundary=%s' % boundary)

        # file
        lines = []
        lines.append('--%s' % boundary)
        lines.append('Content-Disposition: form-data; name="data"; filename="weight.fit"')
        lines.append('Content-Type: application/octet-stream')
        lines.append('')
        lines.append(fbody)

        lines.append('--%s--' % boundary)
        lines.append('')
        r = self.opener.open(req, '\r\n'.join(lines))
        return r.code == 200

    def post_weight(self, date, value):
        """deprecated"""
        if isinstance(date, (datetime.datetime, datetime.date)):
            date = date.strftime('%Y-%m-%d')
        params = {'date': date, 'value': value, 'returnProvidedValues': 'true'}
        r = self.opener.open(self.WEIGHT_INPUT_URL, urllib.urlencode(params))
        return r.code == 200

