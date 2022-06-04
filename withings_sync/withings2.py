"""This module takes care of the communication with Withings."""
from datetime import date, datetime
import logging
import json
import os
import time
import pkg_resources
import requests

log = logging.getLogger("withings")

HOME = os.environ.get("HOME", ".")
AUTHORIZE_URL = "https://account.withings.com/oauth2_user/authorize2"
TOKEN_URL = "https://wbsapi.withings.net/v2/oauth2"
GETMEAS_URL = "https://wbsapi.withings.net/measure?action=getmeas"

APP_CONFIG = os.environ.get(
    "WITHINGS_APP",
    pkg_resources.resource_filename(__name__, "config/withings_app.json"),
)
USER_CONFIG = os.environ.get("WITHINGS_USER", HOME + "/.withings_user.json")


class WithingsException(Exception):
    """Pass WithingsExceptions"""


class WithingsConfig:
    """This class takes care of the Withings config file"""

    config = {}
    config_file = ""

    def __init__(self, config_file):
        self.config_file = config_file
        self.read()

    def read(self):
        """reads config file"""
        try:
            with open(self.config_file, encoding="utf8") as configfile:
                self.config = json.load(configfile)
        except (ValueError, FileNotFoundError):
            log.error("Can't read config file %s", self.config_file)
            self.config = {}

    def write(self):
        """writes config file"""
        with open(self.config_file, "w", encoding="utf8") as configfile:
            json.dump(self.config, configfile, indent=4, sort_keys=True)


class WithingsOAuth2:
    """This class takes care of the Withings OAuth2 authentication"""

    app_config = user_config = None

    def __init__(self):
        app_cfg = WithingsConfig(APP_CONFIG)
        self.app_config = app_cfg.config

        self.user_cfg = WithingsConfig(USER_CONFIG)
        self.user_config = self.user_cfg.config

        if not self.user_config.get("access_token"):
            if not self.user_config.get("authentification_code"):
                self.user_config[
                    "authentification_code"
                ] = self.get_authenticationcode()

            self.get_accesstoken()

        self.refresh_accesstoken()

        self.user_cfg.write()

    def update_config(self):
        """updates config file"""
        self.user_cfg.write()

    def get_authenticationcode(self):
        """get Withings authentication code"""
        params = {
            "response_type": "code",
            "client_id": self.app_config["client_id"],
            "state": "OK",
            "scope": "user.metrics",
            "redirect_uri": self.app_config["callback_url"],
        }

        log.warning(
            "User interaction needed to get Authentification " "Code from Withings!"
        )
        log.warning("")
        log.warning(
            "Open the following URL in your web browser and copy back "
            "the token. You will have *30 seconds* before the "
            "token expires. HURRY UP!"
        )
        log.warning("(This is one-time activity)")
        log.warning("")

        url = AUTHORIZE_URL + "?"

        for key, value in params.items():
            url = url + key + "=" + value + "&"

        log.info(url)
        log.info("")

        authentification_code = input("Token : ")

        return authentification_code

    def get_accesstoken(self):
        """get Withings access token"""
        log.info("Get Access Token")

        params = {
            "action": "requesttoken",
            "grant_type": "authorization_code",
            "client_id": self.app_config["client_id"],
            "client_secret": self.app_config["consumer_secret"],
            "code": self.user_config["authentification_code"],
            "redirect_uri": self.app_config["callback_url"],
        }

        req = requests.post(TOKEN_URL, params)
        resp = req.json()

        status = resp.get("status")
        body = resp.get("body")

        if status != 0:
            log.error("Received error code: %d", status)
            log.error(
                "Check here for an interpretation of this error: "
                "http://developer.withings.com/api-reference#section/Response-status"
            )
            log.error("")
            log.error(
                "If it's regarding an invalid code, try to start the"
                " script again to obtain a new link."
            )

        self.user_config["access_token"] = body.get("access_token")
        self.user_config["refresh_token"] = body.get("refresh_token")
        self.user_config["userid"] = body.get("userid")

    def refresh_accesstoken(self):
        """refresh Withings access token"""
        log.info("Refresh Access Token")

        params = {
            "action": "requesttoken",
            "grant_type": "refresh_token",
            "client_id": self.app_config["client_id"],
            "client_secret": self.app_config["consumer_secret"],
            "refresh_token": self.user_config["refresh_token"],
        }

        req = requests.post(TOKEN_URL, params)
        resp = req.json()

        status = resp.get("status")
        body = resp.get("body")

        if status != 0:
            log.error("Received error code: %d", status)
            log.error(
                "Check here for an interpretation of this error: "
                "http://developer.withings.com/api-reference#section/Response-status"
            )
            log.error("")
            log.error(
                "If it's regarding an invalid code, try to start the"
                " script again to obtain a new link."
            )

        self.user_config["access_token"] = body.get("access_token")
        self.user_config["refresh_token"] = body.get("refresh_token")
        self.user_config["userid"] = body.get("userid")


class WithingsAccount:
    """This class gets measurements from Withings"""

    def __init__(self):
        self.withings = WithingsOAuth2()

    def get_lastsync(self):
        """get last sync timestamp"""
        if not self.withings.user_config.get("last_sync"):
            return int(time.mktime(date.today().timetuple()))
        return self.withings.user_config["last_sync"]

    def set_lastsync(self):
        """set last sync timestamp"""
        self.withings.user_config["last_sync"] = int(time.time())
        log.info("Saving Last Sync")
        self.withings.update_config()

    def get_measurements(self, startdate, enddate):
        """get Withings measurements"""
        log.info("Get Measurements")

        params = {
            "access_token": self.withings.user_config["access_token"],
            # 'meastype': MEASTYPE_WEIGHT,
            "category": 1,
            "startdate": startdate,
            "enddate": enddate,
        }

        req = requests.post(GETMEAS_URL, params)

        measurements = req.json()

        if measurements.get("status") == 0:
            log.debug("Measurements received")
            return [
                WithingsMeasureGroup(g)
                for g in measurements.get("body").get("measuregrps")
            ]
        return None

    def get_height(self):
        """get height from Withings"""
        height = None
        height_timestamp = None
        height_group = None

        log.debug("Get Height")

        params = {
            "access_token": self.withings.user_config["access_token"],
            "meastype": WithingsMeasure.TYPE_HEIGHT,
            "category": 1,
        }

        req = requests.post(GETMEAS_URL, params)

        measurements = req.json()

        if measurements.get("status") == 0:
            log.debug("Height received")

            # there could be multiple height records. use the latest one
            for record in measurements.get("body").get("measuregrps"):
                height_group = WithingsMeasureGroup(record)
                if height is not None:
                    if height_timestamp is not None:
                        if height_group.get_datetime() > height_timestamp:
                            height = height_group.get_height()
                else:
                    height = height_group.get_height()
                    height_timestamp = height_group.get_datetime()

        return height


class WithingsMeasureGroup:
    """This class takes care of the group measurement functions"""

    def __init__(self, measuregrp):
        self._raw_data = measuregrp
        self.grpid = measuregrp.get("grpid")
        self.attrib = measuregrp.get("attrib")
        self.date = measuregrp.get("date")
        self.category = measuregrp.get("category")
        self.measures = [WithingsMeasure(m) for m in measuregrp["measures"]]

    def __iter__(self):
        for measure in self.measures:
            yield measure

    def __len__(self):
        return len(self.measures)

    def get_datetime(self):
        """convenient function to get date & time"""
        return datetime.fromtimestamp(self.date)

    def get_raw_data(self):
        """convenient function to get raw data"""
        return self.measures

    def get_weight(self):
        """convenient function to get weight"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_WEIGHT:
                return round(measure.get_value(), 2)
        return None

    def get_height(self):
        """convenient function to get height"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_HEIGHT:
                return round(measure.get_value(), 2)
        return None

    def get_fat_free_mass(self):
        """convenient function to get fat free mass"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_FAT_FREE_MASS:
                return round(measure.get_value(), 2)
        return None

    def get_fat_ratio(self):
        """convenient function to get fat ratio"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_FAT_RATIO:
                return round(measure.get_value(), 2)
        return None

    def get_fat_mass_weight(self):
        """convenient function to get fat mass weight"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_FAT_MASS_WEIGHT:
                return round(measure.get_value(), 2)
        return None

    def get_diastolic_blood_pressure(self):
        """convenient function to get diastolic blood pressure"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_DIASTOLIC_BLOOD_PRESSURE:
                return round(measure.get_value(), 2)
        return None

    def get_systolic_blood_pressure(self):
        """convenient function to get systolic blood pressure"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_SYSTOLIC_BLOOD_PRESSURE:
                return round(measure.get_value(), 2)
        return None

    def get_heart_pulse(self):
        """convenient function to get heart pulse"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_HEART_PULSE:
                return round(measure.get_value(), 2)
        return None

    def get_temperature(self):
        """convenient function to get temperature"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_TEMPERATURE:
                return round(measure.get_value(), 2)
        return None

    def get_sp02(self):
        """convenient function to get sp02"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_SP02:
                return round(measure.get_value(), 2)
        return None

    def get_body_temperature(self):
        """convenient function to get body temperature"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_BODY_TEMPERATURE:
                return round(measure.get_value(), 2)
        return None

    def get_skin_temperature(self):
        """convenient function to get skin temperature"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_SKIN_TEMPERATURE:
                return round(measure.get_value(), 2)
        return None

    def get_muscle_mass(self):
        """convenient function to get muscle mass"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_MUSCLE_MASS:
                return round(measure.get_value(), 2)
        return None

    def get_hydration(self):
        """convenient function to get hydration"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_HYDRATION:
                return round(measure.get_value(), 2)
        return None

    def get_bone_mass(self):
        """convenient function to get bone mass"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_BONE_MASS:
                return round(measure.get_value(), 2)
        return None

    def get_pulse_wave_velocity(self):
        """convenient function to get pulse wave velocity"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_PULSE_WAVE_VELOCITY:
                return round(measure.get_value(), 2)
        return None


class WithingsMeasure:
    """This class takes care of the individual measurements"""

    TYPE_WEIGHT = 1
    TYPE_HEIGHT = 4
    TYPE_FAT_FREE_MASS = 5
    TYPE_FAT_RATIO = 6
    TYPE_FAT_MASS_WEIGHT = 8
    TYPE_DIASTOLIC_BLOOD_PRESSURE = 9
    TYPE_SYSTOLIC_BLOOD_PRESSURE = 10
    TYPE_HEART_PULSE = 11
    TYPE_TEMPERATURE = 12
    TYPE_SP02 = 54
    TYPE_BODY_TEMPERATURE = 71
    TYPE_SKIN_TEMPERATURE = 73
    TYPE_MUSCLE_MASS = 76
    TYPE_HYDRATION = 77
    TYPE_BONE_MASS = 88
    TYPE_PULSE_WAVE_VELOCITY = 91

    self.withings_table = {
        self.TYPE_WEIGHT: ["Weight", "kg"],
        self.TYPE_HEIGHT: ["Height", "meter"],
        self.TYPE_FAT_FREE_MASS: ["Fat Free Mass", "kg"],
        self.TYPE_FAT_RATIO: ["Fat Ratio", "%"],
        self.TYPE_FAT_MASS_WEIGHT: ["Fat Mass Weight", "kg"],
        self.TYPE_DIASTOLIC_BLOOD_PRESSURE: ["Diastolic Blood Pressure", "mmHg"],
        self.TYPE_SYSTOLIC_BLOOD_PRESSURE: ["Systolic Blood Pressure", "mmHg"],
        self.TYPE_HEART_PULSE: ["Heart Pulse", "bpm"],
        self.TYPE_TEMPERATURE: ["Temperature", "celsius"],
        self.TYPE_SP02: ["SP02", "%"],
        self.TYPE_BODY_TEMPERATURE: ["Body Temperature", "celsius"],
        self.TYPE_SKIN_TEMPERATURE: ["Skin Temperature", "celsius"],
        self.TYPE_MUSCLE_MASS: ["Muscle Mass", "kg"],
        self.TYPE_HYDRATION: ["Hydration", "kg"],
        self.TYPE_BONE_MASS: ["Bone Mass", "kg"],
        self.TYPE_PULSE_WAVE_VELOCITY: ["Pulse Wave Velocity", "m/s"],
    }

    def __init__(self, measure):
        self._raw_data = measure
        self.value = measure.get("value")
        self.type = measure.get("type")
        self.unit = measure.get("unit")
        self.type_s = self.withings_table.get(self.type, ["unknown", ""])[0]
        self.unit_s = self.withings_table.get(self.type, ["unknown", ""])[1]

    def __str__(self):
        return f"{self.type_s}: {self.get_value()} {self.unit_s}"

    def json_dict(self):
        return { f"{self.type_s.replace(' ','_')}": { "Value": round(self.get_value(), 2), "Unit": f'{self.unit_s}'}}

    def get_value(self):
        """get value"""
        return self.value * pow(10, self.unit)
