#!/usr/bin/env python
# -*- coding: utf-8 -*-

from withings2 import WithingsAccount
from garmin import GarminConnect
from fit import FitEncoder_Weight

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
	p.add_option('-f', '--fromdate', type='date', default=date.today(), metavar='<date>')
	p.add_option('-t', '--todate', type='date', default=date.today(), metavar='<date>')
	p.add_option('--no-upload', action='store_true', help="Won't upload to Garmin Connect and output binary-strings to stdout.")
	p.add_option('-v', '--verbose', action='store_true', help='Run verbosely')
	opts, args = p.parse_args()

	sync(**opts.__dict__)


def sync(garmin_username, garmin_password, fromdate, todate, 
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
	fit.finish()

	if no_upload:
		sys.stdout.buffer.write(fit.getvalue())
		return

	out_file = open('test.fit', 'wb')
	out_file.write(fit.getvalue())

	# verbose_print("Fit file: " + fit.getvalue())

	# garmin connect
	garmin = GarminConnect()
	session = garmin.login(garmin_username, garmin_password)
	verbose_print('attempting to upload fit file...\n')
	r = garmin.upload_file(fit.getvalue(), session)
	if r:
		verbose_print('weight.fit has been successfully uploaded!\n')


if __name__ == '__main__':
	main()
