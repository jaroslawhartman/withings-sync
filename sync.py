#!/usr/bin/env python
# -*- coding: utf-8 -*-

from withings import WithingsAccount
from garmin import GarminConnect

from optparse import OptionParser
from optparse import Option
from optparse import OptionValueError
from datetime import date
from datetime import datetime
import time


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
    p.add_option('-v', '--verbose', action='store_true', help='Run verbosely')
    opts, args = p.parse_args()

    sync(**opts.__dict__)


def sync(withings_username, withings_password, withings_shortname,
         garmin_username, garmin_password,
         fromdate, todate, verbose):

    def verbose_print(s):
        if verbose:
            print s

    withings = WithingsAccount(withings_username, withings_password)
    user = withings.get_user_by_shortname(withings_shortname)
    if not user:
        print 'could not find user: %s' % withings_shortname
        return
    if not user.ispublic:
        print 'user %s does not go public withings data' % withings_shortname
        return
    startdate = int(time.mktime(fromdate.timetuple()))
    enddate = int(time.mktime(todate.timetuple())) + 86399
    groups = user.get_measure_groups(startdate=startdate, enddate=enddate)

    # garmin connect
    garmin = GarminConnect()
    garmin.login(garmin_username, garmin_password)

    for group in groups:
        date = group.get_datetime().date()
        weight = group.get_weight()
        garmin.post_weight(date, weight)
        verbose_print('sync done: %s %skg' % (date, weight))


if __name__ == '__main__':
    main()

