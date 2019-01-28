#!/usr/bin/env python

import sys
import requests
import json
import argparse

from datetime import date
from datetime import datetime
import time


class Withings():
	AUTHORIZE_URL = 'https://account.withings.com/oauth2_user/authorize2'
	TOKEN_URL = 'https://account.withings.com/oauth2/token'
	GETMEAS_URL = 'https://wbsapi.withings.net/measure?action=getmeas'
	APP_CONFIG = 'config/withings_app.json'
	USER_CONFIG = 'config/withings_user.json'

	# 1	Weight (kg)
	# 4	Height (meter)
	# 5	Fat Free Mass (kg)
	# 6	Fat Ratio (%)
	# 8	Fat Mass Weight (kg)
	# 9	Diastolic Blood Pressure (mmHg)
	# 10	Systolic Blood Pressure (mmHg)
	# 11	Heart Pulse (bpm) - only for BPM devices
	# 12	Temperature
	# 54	SP02 (%)
	# 71	Body Temperature
	# 73	Skin Temperature
	# 76	Muscle Mass
	# 77	Hydration
	# 88	Bone Mass
	# 91	Pulse Wave Velocity

	MEASTYPE_WEIGHT = 1

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

class WitingsOAuth2(Withings):
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
		print("User interaction needed to get Authentification Code!")
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
		print("Get Access Token")

		params = {
			"grant_type" : "authorization_code",
			"client_id" : self.app_config['client_id'],
			"client_secret" : self.app_config['consumer_secret'],
			"code" : self.user_config['authentification_code'],
			"redirect_uri" : self.app_config['callback_url'],
		}

		req = requests.post(Withings.TOKEN_URL, params )

		accessToken = req.json()

		print(accessToken)

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
		print("Refresh Access Token")

		params = {
			"grant_type" : "refresh_token",
			"client_id" : self.app_config['client_id'],
			"client_secret" : self.app_config['consumer_secret'],
			"refresh_token" : self.user_config['refresh_token'],
		}

		req = requests.post(Withings.TOKEN_URL, params )

		accessToken = req.json()

		print(accessToken)

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
		self.withings = WitingsOAuth2()

	def getMeasurements(self, startdate, enddate):
		print("Get Measurements")

		params = {
			"access_token" : self.withings.user_config['access_token'],
			"meastype" : Withings.MEASTYPE_WEIGHT,
			"category" : 1,
			"startdate" : startdate,
			"enddate" : enddate,
		}

		req = requests.post(Withings.GETMEAS_URL, params )

		measurements = req.json()

		print(measurements)


def main():
	usage = 'usage: sync.py [options]'
	p = argparse.ArgumentParser(usage=usage)
	p.add_argument('-f', '--fromdate', type=date, default=date.today(), metavar='<date>')
	# p.add_argument('-f', '--fromdate', type='date', default=date.today(), metavar='<date>')
	p.add_argument('-t', '--todate', type=date, default=date.today(), metavar='<date>')
	args = p.parse_args()

	print(args)

	fromdate = args.fromdate
	todate = args.todate

	print(fromdate)
	print(todate)

	startdate = int(time.mktime(fromdate.timetuple()))
	enddate = int(time.mktime(todate.timetuple())) + 86399

	print(startdate)
	print(enddate)

	withingsAccount = WithingsAccount()

	withingsAccount.getMeasurements(startdate, enddate)

if __name__ == '__main__':
	main()