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
    UPLOAD_URL = 'http://connect.garmin.com/proxy/upload-service-1.1/json/upload/.fit'
    
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
    
    def _get_cookies(self, record=None, email=None, password=None):

        gcPreResp = requests.get("http://connect.garmin.com/", allow_redirects=False)
        # New site gets this redirect, old one does not
        if gcPreResp.status_code == 200:
            gcPreResp = requests.get("https://connect.garmin.com/signin", allow_redirects=False)
            req_count = int(re.search("j_id(\d+)", gcPreResp.text).groups(1)[0])
            params = {"login": "login", "login:loginUsernameField": email, "login:password": password, "login:signInButton": "Sign In"}
            auth_retries = 3 # Did I mention Garmin Connect is silly?
            for retries in range(auth_retries):
                params["javax.faces.ViewState"] = "j_id%d" % req_count
                req_count += 1
                self._rate_limit()
                resp = requests.post("https://connect.garmin.com/signin", data=params, allow_redirects=False, cookies=gcPreResp.cookies)
                if resp.status_code >= 500 and resp.status_code < 600:
                    raise APIException("Remote API failure")
                if resp.status_code != 302:  # yep
                    if "errorMessage" in resp.text:
                        if retries < auth_retries - 1:
                            time.sleep(1)
                            continue
                        else:
                            raise APIException("Invalid login", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
                    else:
                        raise APIException("Mystery login error %s" % resp.text)
                break
        elif gcPreResp.status_code == 302:
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
                "service": "http://connect.garmin.com/post-auth/login",
                # "redirectAfterAccountLoginUrl": "http://connect.garmin.com/post-auth/login",
                # "redirectAfterAccountCreationUrl": "http://connect.garmin.com/post-auth/login",
                # "webhost": "olaxpw-connect00.garmin.com",
                "clientId": "GarminConnect",
                # "gauthHost": "https://sso.garmin.com/sso",
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
            preResp = requests.get("https://sso.garmin.com/sso/login", params=params)
            if preResp.status_code != 200:
                raise APIException("SSO prestart error %s %s" % (preResp.status_code, preResp.text))
            data["lt"] = re.search("name=\"lt\"\s+value=\"([^\"]+)\"", preResp.text).groups(1)[0]

            ssoResp = requests.post("https://sso.garmin.com/sso/login", params=params, data=data, allow_redirects=False, cookies=preResp.cookies)
            if ssoResp.status_code != 200:
                raise APIException("SSO error %s %s" % (ssoResp.status_code, ssoResp.text))

            ticket_match = re.search("ticket=([^']+)'", ssoResp.text)
            if not ticket_match:
                raise APIException("Invalid login", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
            ticket = ticket_match.groups(1)[0]

            # ...AND WE'RE NOT DONE YET!

            gcRedeemResp1 = requests.get("http://connect.garmin.com/post-auth/login", params={"ticket": ticket}, allow_redirects=False, cookies=gcPreResp.cookies)
            if gcRedeemResp1.status_code != 302:
                raise APIException("GC redeem 1 error %s %s" % (gcRedeemResp1.status_code, gcRedeemResp1.text))

            gcRedeemResp2 = requests.get(gcRedeemResp1.headers["location"], cookies=gcPreResp.cookies, allow_redirects=False)
            if gcRedeemResp2.status_code != 302:
                raise APIException("GC redeem 2 error %s %s" % (gcRedeemResp2.status_code, gcRedeemResp2.text))

        else:
            raise APIException("Unknown GC prestart response %s %s" % (gcPreResp.status_code, gcPreResp.text))

        self._sessionCache.Set(record.ExternalID if record else email, gcPreResp.cookies)

        return gcPreResp.cookies    



    def login(self, username, password):

        cookies = self._get_cookies(email=username, password=password)
        GCusername = requests.get("http://connect.garmin.com/user/username", cookies=cookies).json()["username"]
        sys.stderr.write('Garmin Connect User Name: ' + GCusername + '\n')    
     
        if not len(GCusername):
            raise APIException("Unable to retrieve username", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
        return (cookies)

    def upload_file(self, f, cookie):
        self.opener = self.create_opener(cookie) 
    
    
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

