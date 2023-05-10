"""This module handles the Garmin connectivity."""
import urllib.request
import urllib.error
import urllib.parse
import re
import json
import logging
import cloudscraper


log = logging.getLogger("garmin")


class LoginSucceeded(Exception):
    """Used to raise on LoginSucceeded"""


class LoginFailed(Exception):
    """Used to raise on LoginFailed"""


class APIException(Exception):
    """Used to raise on APIException"""


class GarminConnect:
    """Main GarminConnect class"""

    LOGIN_URL = "https://connect.garmin.com/signin"
    UPLOAD_URL = "https://connect.garmin.com/modern/proxy/upload-service/upload/.fit"

    def create_opener(self, cookie):
        """Garmin opener"""
        this = self

        class _HTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
            def http_error_302(
                self, req, fp, code, msg, headers
            ):  # pylint: disable=too-many-arguments
                if req.get_full_url() == this.LOGIN_URL:
                    raise LoginSucceeded

                return urllib.request.HTTPRedirectHandler.http_error_302(
                    self, req, fp, code, msg, headers
                )

        return urllib.request.build_opener(
            _HTTPRedirectHandler, urllib.request.HTTPCookieProcessor(cookie)
        )

    # From https://github.com/cpfair/tapiriik
    @staticmethod
    def get_session(email=None, password=None):
        """tapiriik get_session code"""
        session = cloudscraper.CloudScraper()

        data = {
            "username": email,
            "password": password,
            "_eventId": "submit",
            "embed": "true",
        }
        params = {
            "service": "https://connect.garmin.com/modern",
            "clientId": "GarminConnect",
            "gauthHost": "https://sso.garmin.com/sso",
            "consumeServiceTicket": "false",
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 "
            + "(KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36",
            "Referer": "https://jhartman.pl",
            "origin": "https://sso.garmin.com",
        }

        # I may never understand what motivates people to mangle a perfectly
        # good protocol like HTTP in the ways they do...
        preresp = session.get(
            "https://sso.garmin.com/sso/signin", params=params, headers=headers
        )
        if preresp.status_code != 200:
            raise APIException(
                f"SSO prestart error {preresp.status_code} {preresp.text}"
            )

        ssoresp = session.post(
            "https://sso.garmin.com/sso/login",
            params=params,
            data=data,
            allow_redirects=False,
            headers=headers,
        )

        if ssoresp.status_code == 429:
            raise APIException(
                "SSO error 429: You are being rate limited: "
                + "The owner of this website (sso.garmin.com) "
                + "has banned you temporarily from accessing this website."
            )

        if ssoresp.status_code != 200 or "temporarily unavailable" in ssoresp.text:
            raise APIException(f"SSO error {ssoresp.status_code} {ssoresp.text}")

        if ">sendEvent('FAIL')" in ssoresp.text:
            raise APIException("Invalid login")

        if ">sendEvent('ACCOUNT_LOCKED')" in ssoresp.text:
            raise APIException("Account Locked")

        if "renewPassword" in ssoresp.text:
            raise APIException("Reset password")

        # self.print_cookies(cookies=session.cookies)

        # ...AND WE'RE NOT DONE YET!

        gcredeemresp = session.get(
            "https://connect.garmin.com/modern", allow_redirects=False, headers=headers
        )
        if gcredeemresp.status_code != 302:
            raise APIException(
                f"GC redeem-start error {gcredeemresp.status_code} {gcredeemresp.text}"
            )

        url_prefix = "https://connect.garmin.com"

        # There are 6 redirects that need to be followed to get the correct cookie
        # ... :(
        max_redirect_count = 7
        current_redirect_count = 1
        while True:
            url = gcredeemresp.headers["location"]

            # Fix up relative redirects.
            if url.startswith("/"):
                url = url_prefix + url
            url_prefix = "/".join(url.split("/")[:3])
            gcredeemresp = session.get(url, allow_redirects=False)

            if (
                current_redirect_count >= max_redirect_count
                and gcredeemresp.status_code != 200
            ):
                raise APIException(
                    f"GC redeem {current_redirect_count}/"
                    "{max_redirect_count} error "
                    "{gcredeemresp.status_code} "
                    "{gcredeemresp.text}"
                )

            if gcredeemresp.status_code in [200, 404]:
                break

            current_redirect_count += 1
            if current_redirect_count > max_redirect_count:
                break

        # GarminConnect.print_cookies(session.cookies)
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

    @staticmethod
    def print_cookies(cookies):
        """print cookies"""
        log.debug("Cookies: ")
        for key, value in list(cookies.items()):
            log.debug(" %s = %s", key, value)

    @staticmethod
    def login(username, password):
        """login to Garmin"""
        session = GarminConnect.get_session(email=username, password=password)
        try:
            dashboard = session.get("http://connect.garmin.com/modern")
            userdata = GarminConnect.get_json(dashboard.text, "VIEWER_SOCIAL_PROFILE")
            username = userdata["userName"]

            log.info("Garmin Connect User Name: %s", username)

        except Exception as exception:  # pylint: disable=broad-except
            log.error(exception)
            log.error(
                "Unable to retrieve Garmin username! Most likely: "
                "incorrect Garmin login or password!"
            )
            log.debug(dashboard.text)

        return session

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
