#!/usr/bin/env python
# -*- coding: utf-8 -*-

from withings import WithingsAccount
from garmin import GarminConnect
from fit import FitEncoder_Weight

from optparse import OptionParser
from optparse import Option
from optparse import OptionValueError
from datetime import date
from datetime import datetime
import time
import sys


WITHINGS_USERNMAE = ''
WITHINGS_PASSWORD = ''
WITHINGS_SHORTNAME = ''

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
    p.add_option('--withings-username', '--wu',
                 default=WITHINGS_USERNMAE, metavar='<user>', help='username to login Withings Web Service.')
    p.add_option('--withings-password', '--wp',
                 default=WITHINGS_PASSWORD, metavar='<pass>', help='password to login Withings Web Service.')
    p.add_option('--withings-shortname', '--ws',
                 default=WITHINGS_SHORTNAME, metavar='<name>', help='your shortname used in Withings.')
    p.add_option('--garmin-username', '--gu',
                 default=GARMIN_USERNAME, metavar='<user>', help='username to login Garmin Connect.')
    p.add_option('--garmin-password', '--gp',
                 default=GARMIN_PASSWORD, metavar='<pass>', help='password to login Garmin Connect.')
    p.add_option('-f', '--fromdate', type='date', default=date.today(), metavar='<date>')
    p.add_option('-t', '--todate', type='date', default=date.today(), metavar='<date>')
    p.add_option('--no-upload', action='store_true', help="Won't upload to Garmin Connect and output binary-strings to stdout.")
    p.add_option('-v', '--verbose', action='store_true', help='Run verbosely')
    opts, args = p.parse_args()

    sync(**opts.__dict__)


def sync(withings_username, withings_password, withings_shortname,
         garmin_username, garmin_password,
         fromdate, todate, no_upload, verbose):

    def verbose_print(s):
        if verbose:
            if no_upload:
                sys.stderr.write(s)
            else:
                sys.stdout.write(s)

    # Withings API
    withings = WithingsAccount(withings_username, withings_password)
    user = withings.get_user_by_shortname(withings_shortname)
    if not user:
        print 'could not find user: %s' % withings_shortname
        return
    if not user.ispublic:
        print 'user %s has not opened withings data' % withings_shortname
        return
    startdate = int(time.mktime(fromdate.timetuple()))
    enddate = int(time.mktime(todate.timetuple())) + 86399
    groups = user.get_measure_groups(startdate=startdate, enddate=enddate)

    # create fit file
    verbose_print('generating fit file...\n')
    fit = FitEncoder_Weight()
    fit.write_file_info()
    fit.write_file_creator()

    for group in groups:
        # get extra physical measurements

        from measurements import Measurements
        measurements = Measurements()

        dt = group.get_datetime()
        weight = group.get_weight()
        fat_ratio = group.get_fat_ratio()
        fit.write_device_info(timestamp=dt)
        fit.write_weight_scale(timestamp=dt,
            weight=weight,
            percent_fat=fat_ratio,
            percent_hydration=measurements.getPercentHydration()
            )
        verbose_print('appending weight scale record... %s %skg %s%%\n' % (dt, weight, fat_ratio))
    fit.finish()

    if no_upload:
        sys.stdout.write(fit.getvalue())
        return

	verbose_print("Fit file: " + fit.getvalue())

    # garmin connect
    garmin = GarminConnect()
    session = garmin.login(garmin_username, garmin_password)
    verbose_print('attempting to upload fit file...\n')
    r = garmin.upload_file(fit.getvalue(), session)
    if r:
        verbose_print('weight.fit has been successfully uploaded!\n')


if __name__ == '__main__':
    main()
