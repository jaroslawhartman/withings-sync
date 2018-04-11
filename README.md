# withings-garmin-v2

**NOTE: Withings is a legacy name of Nokia Health Body / Body Cardio Scales. Feel free to use this script with Nokia products as well **

## References

* Based on withings-garmin by Masayuki Hamasaki, improved to support SSO authorization in Garmin Connect 2.

* SSO authorization derived from https://github.com/cpfair/tapiriik

## Pre-requisites

* Python 2.5 - 2.7
* 'Requests: HTTP for Humans' (http://docs.python-requests.org/en/latest/)

```
$ sudo easy_install requests

```

* simplejson

```
$ sudo easy_install simplejson
```

## Usage

```
Usage: $python sync.py [options]

Options:
  -h, --help            show this help message and exit
  --withings-username=<user>, --wu=<user>
                        username to login Withings Web Service.
  --withings-password=<pass>, --wp=<pass>
                        password to login Withings Web Service.
  --withings-shortname=<name>, --ws=<name>
                        your shortname used in Withings.
  --garmin-username=<user>, --gu=<user>
                        username to login Garmin Connect.
  --garmin-password=<pass>, --gp=<pass>
                        password to login Garmin Connect.
  -f <date>, --fromdate=<date>
  -t <date>, --todate=<date>
  --no-upload           Won't upload to Garmin Connect and output binary-
                        string to stdout.
  -v, --verbose         Run verbosely

```

## Tips

* Export to a file
```
$ python sync.py --no-upload > weight.fit
```

* You can hardcode your usernames and passwords in the script (`sync.py`):

```
WITHINGS_USERNMAE = ''
WITHINGS_PASSWORD = ''
WITHINGS_SHORTNAME = ''

GARMIN_USERNAME = ''
GARMIN_PASSWORD = ''
```
