# withings-sync

A tool for synchronisation of the Withings API to:

- Garmin Connect
- Trainer Road
- raw JSON output

## References

* SSO authorization derived from https://github.com/cpfair/tapiriik
* TrainerRoad API from https://github.com/stuwilkins/python-trainerroad 

## Credits / Authors

* Based on [withings-garmin](https://github.com/ikasamah/withings-garmin) by Masayuki Hamasaki, improved to support SSO authorization in Garmin Connect 2.
* Based on [withings-garmin-v2](https://github.com/jaroslawhartman/withings-garmin-v2) by Jarek Hartman, improved Python 3 compatability, code-style and setuptools packaging, Kubernetes and Docker support.


## Usage

```
usage: withings-sync [-h] [--withings-userid WITHINGS_USERID] [--garmin-upload] [--trainerroad-upload] [--fromdate DATE]
                     [--todate DATE] [--to-fit] [--to-json] [--output BASENAME] [--verbose]

A tool for synchronisation of Withings (ex. Nokia Health Body) to Garmin Connect and Trainer Road or to provide a json string.

optional arguments:
  -h, --help            show this help message and exit
  --withings-userid WITHINGS_USERID, --wuid WITHINGS_USERID
                        API userid to use for Withings.
  --garmin-upload, --gu
                        upload to Garmin Connect.
  --trainerroad-upload, --tu
                        upload to TrainerRoad.
  --fromdate DATE, -f DATE
  --todate DATE, -t DATE
  --to-fit, -F          Write output file in FIT format.
  --to-json, -J         Write output file in JSON format.
  --output BASENAME, -o BASENAME
                        Write downloaded measurements to file.
  --verbose, -v         Run verbosely
```

### Obtaining Withings Authorization Code

When running for a very first time, you need to obtain Withings authorization:

```bash
$ withings-sync -f 2019-01-25 -v
Can't read config file config/withings_user.json
User interaction needed to get Authentification Code from Withings!

Open the following URL in your web browser and copy back the token. You will have *30 seconds* before the token expires. HURRY UP!
(This is one-time activity)

https://account.withings.com/oauth2_user/authorize2?response_type=code&client_id=183e03e1f363110b3551f96765c98c10e8f1aa647a37067a1cb64bbbaf491626&state=OK&scope=user.metrics&redirect_uri=https://wieloryb.uk.to/withings/withings.html&

Token :
```

You need to visit the URL listed by the script and then - copy Authentification Code back to the prompt.

This is one-time activity and it will not be needed to repeat.


## Tips

### Garmin SSO errors

Some users reported errors raised by the Garmin SSO login:

```
withings_sync.garmin.APIException: SSO error 401
```

or 

```
withings_sync.garmin.APIException: SSO error 403
```

These errors are raised if a user tries to login too frequently.
E.g. by running the script every 10 minutes.

**We recommend to run the script around 8-10 times per day (every 2-3 hours).**

See also: https://github.com/jaroslawhartman/withings-sync/issues/31

