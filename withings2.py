#!/usr/bin/env python

import sys
import requests
import json
import argparse

from datetime import date
from datetime import datetime
import time

class WithingsException(Exception):
    pass

class Withings():
	AUTHORIZE_URL = 'https://account.withings.com/oauth2_user/authorize2'
	TOKEN_URL = 'https://account.withings.com/oauth2/token'
	GETMEAS_URL = 'https://wbsapi.withings.net/measure?action=getmeas'
	APP_CONFIG = 'config/withings_app.json'
	USER_CONFIG = 'config/withings_user.json'

class WithingsConfig(Withings):
	config = {}
	config_file = ""

	def __init__(self, config_file):
		self.config_file = config_file
		self.read()

	def read(self):
		try:
			with open(self.config_file) as f:
				self.config = json.load(f)
		except (ValueError, FileNotFoundError):
			print("Can't read config file " + self.config_file)
			self.config = {}

	def write(self):
		with open(self.config_file, "w") as f:
			json.dump(self.config, f, indent=4, sort_keys=True)

class WithingsOAuth2(Withings):
	app_config = user_config = None

	def __init__(self):
		app_cfg = WithingsConfig(Withings.APP_CONFIG)
		self.app_config = app_cfg.config

		user_cfg = WithingsConfig(Withings.USER_CONFIG)
		self.user_config = user_cfg.config

		if not self.user_config.get('access_token'):
			if not self.user_config.get('authentification_code'):
				self.user_config['authentification_code'] = self.getAuthenticationCode()

			self.getAccessToken()

		self.refreshAccessToken()

		app_cfg.write()
		user_cfg.write()

	def getAuthenticationCode(self):
		params = {
			"response_type" : "code",
			"client_id" : self.app_config['client_id'],
			"state" : "OK",
			"scope" : "user.metrics",
			"redirect_uri" : self.app_config['callback_url'],
		}

		print("***************************************")
		print("*         W A R N I N G               *")
		print("***************************************")
		print()
		print("User interaction needed to get Authentification Code from Withings!")
		print()
		print("Open the following URL in your web browser and copy back the token. You will have *30 seconds* before the token expires. HURRY UP!")
		print("(This is one-time activity)")
		print()
		
		url = Withings.AUTHORIZE_URL + '?'

		for key, value in params.items():
			url = url + key + '=' + value + "&"

		print(url)
		print()

		authentification_code = input("Token : ")

		return authentification_code
	
	def getAccessToken(self):
		print("Withings: Get Access Token")

		params = {
			"grant_type" : "authorization_code",
			"client_id" : self.app_config['client_id'],
			"client_secret" : self.app_config['consumer_secret'],
			"code" : self.user_config['authentification_code'],
			"redirect_uri" : self.app_config['callback_url'],
		}

		req = requests.post(Withings.TOKEN_URL, params )

		accessToken = req.json()

		if(accessToken.get('errors')):
			print("Received error(s):")
			for message in accessToken.get('errors'):
				error = message.get('message')
				print("  " + error)
				if "invalid code" in error:
					print("Removing invalid authentification_code")
					self.user_config['authentification_code'] = ''

			print()
			print("If it's regarding an invalid code, try to start the script again to obtain a new link.")

		self.user_config['access_token'] = accessToken.get('access_token')
		self.user_config['refresh_token'] = accessToken.get('refresh_token')
		self.user_config['userid'] = accessToken.get('userid')

	def refreshAccessToken(self):
		print("Withings: Refresh Access Token")

		params = {
			"grant_type" : "refresh_token",
			"client_id" : self.app_config['client_id'],
			"client_secret" : self.app_config['consumer_secret'],
			"refresh_token" : self.user_config['refresh_token'],
		}

		req = requests.post(Withings.TOKEN_URL, params )

		accessToken = req.json()

		if(accessToken.get('errors')):
			print("Received error(s):")
			for message in accessToken.get('errors'):
				error = message.get('message')
				print("  " + error)
				if "invalid code" in error:
					print("Removing invalid authentification_code")
					self.user_config['authentification_code'] = ''

			print()
			print("If it's regarding an invalid code, try to start the script again to obtain a new link.")

		self.user_config['access_token'] = accessToken.get('access_token')
		self.user_config['refresh_token'] = accessToken.get('refresh_token')
		self.user_config['userid'] = accessToken.get('userid')

class WithingsAccount(Withings):
	def __init__(self):
		self.withings = WithingsOAuth2()

	def getMeasurements(self, startdate, enddate):
		print("Withings: Get Measurements")

		params = {
			"access_token" : self.withings.user_config['access_token'],
			# "meastype" : Withings.MEASTYPE_WEIGHT,
			"category" : 1,
			"startdate" : startdate,
			"enddate" : enddate,
		}

		req = requests.post(Withings.GETMEAS_URL, params )

		measurements = req.json()

		if measurements.get('status') == 0:
			print("   Measurements received")

			return [WithingsMeasureGroup(g) for g in measurements.get('body').get('measuregrps')]

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

    def get_muscle_mass(self):
        """convinient function to get muscle mass"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_MUSCLE_MASS:
                return measure.get_value()
        return None

    def get_hydration(self):
        """convinient function to get hydration"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_HYDRATION:
                return measure.get_value()
        return None

    def get_bone_mass(self):
        """convinient function to get bone mass"""
        for measure in self.measures:
            if measure.type == WithingsMeasure.TYPE_BONE_MASS:
                return measure.get_value()
        return None

class WithingsMeasure(object):
    TYPE_WEIGHT = 1
    TYPE_HEIGHT = 4
    TYPE_FAT_FREE_MASS = 5
    TYPE_FAT_RATIO = 6
    TYPE_FAT_MASS_WEIGHT = 8
    TYPE_MUSCLE_MASS = 76
    TYPE_HYDRATION = 77
    TYPE_BONE_MASS = 88

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

