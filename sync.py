#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from withings2 import WithingsAccount
from garmin import GarminConnect
from fit import FitEncoder_Weight
import trainerroad

from optparse import OptionParser
from optparse import Option
from optparse import OptionValueError
from datetime import date
from datetime import datetime

import json
import time
import sys

GARMIN_USERNAME = ''
GARMIN_PASSWORD = ''

TRAINERROAD_USERNAME = ''
TRAINERROAD_PASSWORD = ''

class DateOption(Option):
	def check_date(option, opt, value):
		valid_formats = ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']
		for f in valid_formats:
			try:
				dt = datetime.strptime(value, f)
				return dt.date()
			except ValueError:
				pass
		raise OptionValueError('option %s: invalid date or format: %s. use following format: %s'
								 % (opt, value, ','.join(valid_formats)))
	TYPES = Option.TYPES + ('date',)
	TYPE_CHECKER = Option.TYPE_CHECKER.copy()
	TYPE_CHECKER['date'] = check_date


def main():
	usage = 'usage: sync.py [options]'
	p = OptionParser(usage=usage, option_class=DateOption)
	p.add_option('--garmin-username', '--gu',
				 default=GARMIN_USERNAME, type='string', metavar='<user>', help='username to login Garmin Connect.')
	p.add_option('--garmin-password', '--gp',
				 default=GARMIN_PASSWORD, type='string', metavar='<pass>', help='password to login Garmin Connect.')
	p.add_option('--trainerroad-username', '--tu', 
				 default=TRAINERROAD_USERNAME, type='string', metavar='<user>', help='username to login TrainerRoad.')	
	p.add_option('--trainerroad-password', '--tp', 
				 default=TRAINERROAD_PASSWORD, type='string', metavar='<user>', help='username to login TrainerRoad.')					 
	p.add_option('-f', '--fromdate', type='date', default=date.today(), metavar='<date>')
	p.add_option('-t', '--todate', type='date', default=date.today(), metavar='<date>')
	p.add_option('--no-upload', action='store_true', help="Won't upload to Garmin Connect and output binary-strings to stdout.")
	p.add_option('-v', '--verbose', action='store_true', help='Run verbosely')
	opts, args = p.parse_args()

	sync(**opts.__dict__)


def sync(garmin_username, garmin_password, trainerroad_username, trainerroad_password, fromdate, todate, 
		 no_upload, verbose):

	def verbose_print(s):
		if verbose:
			if no_upload:
				sys.stderr.write(s)
			else:
				sys.stdout.write(s)

	# Withings API
	withings = WithingsAccount()

	startdate = int(time.mktime(fromdate.timetuple()))
	enddate = int(time.mktime(todate.timetuple())) + 86399

	groups = withings.getMeasurements(startdate=startdate, enddate=enddate)

	# create fit file
	verbose_print('generating fit file...\n')
	fit = FitEncoder_Weight()
	fit.write_file_info()
	fit.write_file_creator()
	
	last_dt = None
	last_weight = 0

	for group in groups:
		# get extra physical measurements

		dt = group.get_datetime()
		weight = group.get_weight()
		fat_ratio = group.get_fat_ratio()
		muscle_mass = group.get_muscle_mass()
		hydration = group.get_hydration()
		bone_mass = group.get_bone_mass()

		fit.write_device_info(timestamp=dt)
		fit.write_weight_scale(timestamp=dt,
			weight=weight,
			percent_fat=fat_ratio,
			percent_hydration=(hydration*100.0/weight) if (hydration and weight) else None,
			bone_mass=bone_mass,
			muscle_mass=muscle_mass
			)
		verbose_print('appending weight scale record... %s %skg %s%%\n' % (dt, weight, fat_ratio))
		last_dt = dt
		last_weight = weight
	fit.finish()


	# garmin connect
	
	if trainerroad_username and last_weight > 0:
		print('Trainerroad username set -- attempting to sync')
		print(" Last weight {}".format(last_weight))
		print(" Measured {}".format(last_dt))
		
		tr = trainerroad.TrainerRoad(trainerroad_username, trainerroad_password)
		tr.connect()
		print ("Current TrainerRoad weight: {} kg ".format(tr.weight))
		print ("Updating TrainerRoad weight to {} kg".format(last_weight))
		tr.weight = round(last_weight, 1)
		tr.disconnect()
		print ("TrainerRoad update done!\n")
		
		
	else:
		print('No Trainerroad username or a new measurement - skipping sync')	
		
		
	if no_upload:
		sys.stdout.buffer.write(fit.getvalue())
		return		
	
	if garmin_username:
		garmin = GarminConnect()
		session = garmin.login(garmin_username, garmin_password)
		verbose_print('attempting to upload fit file...\n')
		r = garmin.upload_file(fit.getvalue(), session)
		if r:
			print("Fit file uploaded to Garmin Connect")
	else:
		print('No Garmin username - skipping sync\n')	


if __name__ == '__main__':
	main()
