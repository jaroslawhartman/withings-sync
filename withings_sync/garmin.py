from datetime import timedelta
import urllib.request
import httpx
import urllib.error
import urllib.parse
import re
import sys
import json
import logging

log = logging.getLogger('garmin')


class LoginSucceeded(Exception):
    pass


class LoginFailed(Exception):
    pass


class APIException(Exception):
    pass


class GarminConnect(object):
    LOGIN_URL = 'https://connect.garmin.com/signin'
    UPLOAD_URL = 'https://connect.garmin.com/modern/proxy/upload-service/upload/.fit'

    def create_opener(self, cookie):
        this = self

        class _HTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                if req.get_full_url() == this.LOGIN_URL:
                    raise LoginSucceeded

                return urllib.request.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)

        return urllib.request.build_opener(_HTTPRedirectHandler, urllib.request.HTTPCookieProcessor(cookie))

    # From https://github.com/cpfair/tapiriik

    def _get_session(self, record=None, email=None, password=None):
        session = httpx.Client(http2=True)

        # JSIG CAS, cool I guess.
        # Not quite OAuth though, so I'll continue to collect raw credentials.
        # Commented stuff left in case this ever breaks because of missing parameters...
        data = {
            'username': email,
            'password': password,
            '_eventId': 'submit',
            'embed': 'true',
            # 'displayNameRequired': 'false'
        }
        params = {
            'service': 'https://connect.garmin.com/modern',
            # 'redirectAfterAccountLoginUrl': 'http://connect.garmin.com/modern',
            # 'redirectAfterAccountCreationUrl': 'http://connect.garmin.com/modern',
            # 'webhost': 'olaxpw-connect00.garmin.com',
            'clientId': 'GarminConnect',
            'gauthHost': 'https://sso.garmin.com/sso',
            # 'rememberMeShown': 'true',
            # 'rememberMeChecked': 'false',
            'consumeServiceTicket': 'false',
            # 'id': 'gauth-widget',
            # 'embedWidget': 'false',
            # 'cssUrl': 'https://static.garmincdn.com/com.garmin.connect/ui/src-css/gauth-custom.css',
            # 'source': 'http://connect.garmin.com/en-US/signin',
            # 'createAccountShown': 'true',
            # 'openCreateAccount': 'false',
            # 'usernameShown': 'true',
            # 'displayNameShown': 'false',
            # 'initialFocus': 'true',
            # 'locale': 'en'
        }

        headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
                'Referer': 'https://jhartman.pl',
                'origin': 'https://sso.garmin.com'
            }

        # I may never understand what motivates people to mangle a perfectly good protocol like HTTP in the ways they do...
        preResp = session.get('https://sso.garmin.com/sso/signin', params=params, headers=headers)
        if preResp.status_code != 200:
            raise APIException('SSO prestart error %s %s' % (preResp.status_code, preResp.text))

        ssoResp = session.post('https://sso.garmin.com/sso/login', params=params, data=data, headers=headers)
        
        if ssoResp.status_code != 200 or 'temporarily unavailable' in ssoResp.text:
            raise APIException('SSO error %s %s' % (ssoResp.status_code, ssoResp.text))

        if '>sendEvent(\'FAIL\')' in ssoResp.text:
            raise APIException('Invalid login')
        
        if '>sendEvent(\'ACCOUNT_LOCKED\')' in ssoResp.text:
            raise APIException('Account Locked')

        if 'renewPassword' in ssoResp.text:
            raise APIException('Reset password')

        # self.print_cookies(cookies=session.cookies)

        # ...AND WE'RE NOT DONE YET!

        gcRedeemResp = session.get('https://connect.garmin.com/modern', headers=headers)
        if gcRedeemResp.status_code != 302:
            raise APIException(f'GC redeem-start error {gcRedeemResp.status_code} {gcRedeemResp.text}')

        url_prefix = 'https://connect.garmin.com'

        # There are 6 redirects that need to be followed to get the correct cookie
        # ... :(
        max_redirect_count = 7
        current_redirect_count = 1
        while True:
            url = gcRedeemResp.headers['location']

            # Fix up relative redirects.
            if url.startswith('/'):
                url = url_prefix + url
            url_prefix = '/'.join(url.split('/')[:3])
            gcRedeemResp = session.get(url)

            if (current_redirect_count >= max_redirect_count and
                gcRedeemResp.status_code != 200):
                raise APIException(f'GC redeem {current_redirect_count}/'
                                   '{max_redirect_count} error '
                                   '{gcRedeemResp.status_code} '
                                   '{gcRedeemResp.text}')

            if gcRedeemResp.status_code in [200, 404]:
                break

            current_redirect_count += 1
            if current_redirect_count > max_redirect_count:
                break

        # self.print_cookies(session.cookies)
        session.headers.update(headers)

        return session


    @staticmethod
    def get_json(page_html, key):
        """Return json from text."""
        found = re.search(key + r" = (\{.*\});", page_html, re.M)
        if found:
            json_text = found.group(1).replace('\\"', '"')
            return json.loads(json_text)
        return None


    def print_cookies(self, cookies):
        log.debug('Cookies: ')
        for key, value in list(cookies.items()):
            log.debug(' %s = %s', key, value)


    def login(self, username, password):

        session = self._get_session(email=username, password=password)

        try:
            dashboard = session.get('http://connect.garmin.com/modern',follow_redirects=True)
            userdata = GarminConnect.get_json(dashboard.text, "VIEWER_SOCIAL_PROFILE")
            username = userdata['userName']

            log.info('Garmin Connect User Name: %s', username)

        except Exception as e:
            log.error(e)
            log.error('Unable to retrieve Garmin username! Most likely: '
                      'incorrect Garmin login or password!')
            log.debug(dashboard.text)

        return session

    def upload_file(self, f, session):
        files = {
            'data': (
                'withings.fit', f
            )
        }

        res = session.post(self.UPLOAD_URL,
                           files=files,
                           headers={'nk': 'NT'})

        try:
            resp = res.json()

            if 'detailedImportResult' not in resp:
                raise KeyError
        except (ValueError, KeyError):
            if res.status_code == 204:   # HTTP result 204 - 'no content'
                log.error('No data to upload, try to use --fromdate and --todate')
            else:
                log.error('Bad response during GC upload: %s', res.status_code)

        return res.status_code in [200, 201, 204]
