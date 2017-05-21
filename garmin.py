# -*- coding: utf-8 -*-

from sessioncache import SessionCache
from datetime import datetime, timedelta
import urllib2
import urllib
import datetime
import requests
import re
import sys

class LoginSucceeded(Exception):
    pass


class LoginFailed(Exception):
    pass


class GarminConnect(object):
    LOGIN_URL = 'https://connect.garmin.com/signin'
    UPLOAD_URL = 'https://connect.garmin.com/modern/proxy/upload-service/upload/.fit'
    
    _sessionCache = SessionCache(lifetime=timedelta(minutes=30), freshen_on_get=True)
    
    def create_opener(self, cookie):
        this = self
        class _HTTPRedirectHandler(urllib2.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                if req.get_full_url() == this.LOGIN_URL:
                    raise LoginSucceeded
                return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        return urllib2.build_opener(_HTTPRedirectHandler, urllib2.HTTPCookieProcessor(cookie))            
        
    ##############################################
    # From https://github.com/cpfair/tapiriik
    
    def _get_session(self, record=None, email=None, password=None):
        session = requests.Session()
        
        # JSIG CAS, cool I guess.
        # Not quite OAuth though, so I'll continue to collect raw credentials.
        # Commented stuff left in case this ever breaks because of missing parameters...
        data = {
            "username": email,
            "password": password,
            "_eventId": "submit",
            "embed": "true",
            # "displayNameRequired": "false"
        }
        params = {
            "service": "https://connect.garmin.com/post-auth/login",
            "redirectAfterAccountLoginUrl": "http://connect.garmin.com/post-auth/login",
            "redirectAfterAccountCreationUrl": "http://connect.garmin.com/post-auth/login",
            # "webhost": "olaxpw-connect00.garmin.com",
            "clientId": "GarminConnect",
            "gauthHost": "https://sso.garmin.com/sso",
            # "rememberMeShown": "true",
            # "rememberMeChecked": "false",
            "consumeServiceTicket": "false",
            # "id": "gauth-widget",
            # "embedWidget": "false",
            # "cssUrl": "https://static.garmincdn.com/com.garmin.connect/ui/src-css/gauth-custom.css",
            # "source": "http://connect.garmin.com/en-US/signin",
            # "createAccountShown": "true",
            # "openCreateAccount": "false",
            # "usernameShown": "true",
            # "displayNameShown": "false",
            # "initialFocus": "true",
            # "locale": "en"
        }
        
        # I may never understand what motivates people to mangle a perfectly good protocol like HTTP in the ways they do...
        preResp = session.get("https://sso.garmin.com/sso/login", params=params)
        if preResp.status_code != 200:
            raise APIException("SSO prestart error %s %s" % (preResp.status_code, preResp.text))
            
        ssoResp = session.post("https://sso.garmin.com/sso/login", params=params, data=data, allow_redirects=False)
        if ssoResp.status_code != 200 or "temporarily unavailable" in ssoResp.text:
            raise APIException("SSO error %s %s" % (ssoResp.status_code, ssoResp.text))

        if ">sendEvent('FAIL')" in ssoResp.text:
            raise APIException("Invalid login", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
        if ">sendEvent('ACCOUNT_LOCKED')" in ssoResp.text:
            raise APIException("Account Locked", block=True, user_exception=UserException(UserExceptionType.Locked, intervention_required=True))

        if "renewPassword" in ssoResp.text:
            raise APIException("Reset password", block=True, user_exception=UserException(UserExceptionType.RenewPassword, intervention_required=True))

        # self.print_cookies(cookies=session.cookies)

        # ...AND WE'RE NOT DONE YET!
        
        gcRedeemResp = session.get("https://connect.garmin.com/post-auth/login", allow_redirects=False)
        if gcRedeemResp.status_code != 302:
            raise APIException("GC redeem-start error %s %s" % (gcRedeemResp.status_code, gcRedeemResp.text))

        url_prefix = "https://connect.garmin.com"

        # There are 6 redirects that need to be followed to get the correct cookie
        # ... :(
        max_redirect_count = 7
        current_redirect_count = 1
        while True:
            url = gcRedeemResp.headers["location"]

            # Fix up relative redirects.
            if url.startswith("/"):
                url = url_prefix + url
            url_prefix = "/".join(url.split("/")[:3])
            gcRedeemResp = session.get(url, allow_redirects=False)

            if current_redirect_count >= max_redirect_count and gcRedeemResp.status_code != 200:
                raise APIException("GC redeem %d/%d error %s %s" % (current_redirect_count, max_redirect_count, gcRedeemResp.status_code, gcRedeemResp.text))
            if gcRedeemResp.status_code == 200 or gcRedeemResp.status_code == 404:
                break
            current_redirect_count += 1
            if current_redirect_count > max_redirect_count:
                break

        self._sessionCache.Set(record.ExternalID if record else email, session.cookies)
        
        # self.print_cookies(session.cookies)

        return session  

    def print_cookies(self, cookies):
            print "Cookies"
            
            for key, value in cookies.items():
                print "Key: " + key + ", " + value

    def login(self, username, password):

        session = self._get_session(email=username, password=password)
        res = session.get("https://connect.garmin.com/user/username")
        GCusername = res.json()["username"]
        
        sys.stderr.write('Garmin Connect User Name: ' + GCusername + '\n')    
     
        if not len(GCusername):
            raise APIException("Unable to retrieve username", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
        return (session)

    def upload_file(self, f, session):
        files = {"data": ("withings.fit", f)}

        res = session.post(self.UPLOAD_URL,
                           files=files,
                           headers={"nk": "NT"}) 

        try:
            resp = res.json()["detailedImportResult"]
        except ValueError:
            if(res.status_code == 204):   # HTTP result 204 - "no content"
                sys.stderr.write('No data to upload, try to use --fromdate and --todate\n')
            else:
                print "Bad response during GC upload: " + str(res.status_code)
                raise APIException("Bad response during GC upload: %s %s" % (res.status_code, res.text))

        return (res.status_code == 200 or res.status_code == 201 or res.status_code == 204)

