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

## Installation

```bash
$ pip install withings-sync
```

## Usage

```
usage: withings-sync [-h] [--withings-userid WITHINGS_USERID] [--garmin-upload] [--trainerroad-upload] [--fromdate DATE]
                     [--todate DATE] [--to-fit] [--to-json] [--output BASENAME] [--no-upload] [--verbose]

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
  --no-upload           Won't upload to Garmin Connect or TrainerRoad.
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

### Docker

```
$ docker pull ghcr.io/jaroslawhartman/withings-sync:master
```

First start to ensure the script can start successfully:


Obtaining Withings authorisation:

```
$ docker run -v $HOME:/root --interactive --tty --name withings ghcr.io/jaroslawhartman/withings-sync:master --garmin-username=<username> --garmin-password=<password>

Can't read config file config/withings_user.json
User interaction needed to get Authentification Code from Withings!

Open the following URL in your web browser and copy back the token. You will have *30 seconds* before the token expires. HURRY UP!
(This is one-time activity)

https://account.withings.com/oauth2_user/authorize2?response_type=code&client_id=183e03e1f363110b3551f96765c98c10e8f1aa647a37067a1cb64bbbaf491626&state=OK&scope=user.metrics&redirect_uri=https://wieloryb.uk.to/withings/withings.html&

Token : <token>
Withings: Get Access Token
Withings: Refresh Access Token
Withings: Get Measurements
   Measurements received
JaHa.WAW.PL
Garmin Connect User Name: JaHa.WAW.PL
Fit file uploaded to Garmin Connect
```

And for subsequent runs:

```
$ docker start -i withings
Withings: Refresh Access Token
Withings: Get Measurements
   Measurements received
JaHa.WAW.PL
Garmin Connect User Name: JaHa.WAW.PL
Fit file uploaded to Garmin Connect
```

### Run a periodic Kubernetes job

Edit the credentials in `contrib/k8s-job.yaml` and run:

```bash
$ kubectl apply -f contrib/k8s-job.yaml
```

### For advanced users - registering own Withings application

The script has been registered as a Withings application and got assigned `Client ID` and `Consumer Secret`. If you wish to create your own application - feel free! 


* First you need a Withings account. [Sign up here](https://account.withings.com/connectionuser/account_create).
* Then you need a a Withings developer app registered. [Create your app here](https://account.withings.com/partner/add_oauth2).

Note, registering it is quite cumbersome, as you need to have a callback URL and an Icon. Anyway, when done, you should have the following identifiers:

| Identfier       |  Example                                                           |
|-----------------|--------------------------------------------------------------------|
| Client ID       | `183e03.................765c98c10e8f1aa647a37067a1......baf491626` |
| Consumer Secret | `a75d65.................4c16719ef7bd69fa7c5d3fd0ea......ed48f1765` |
| Callback URI    | `https://jhartman.pl/withings/notify`                              |

Configure them in `config/withings_app.json`, for example:

```
{
    "callback_url": "https://wieloryb.uk.to/withings/withings.html",
    "client_id": "183e0******0b3551f96765c98c1******b64bbbaf491626",
    "consumer_secret": "a75d65******1df1514c16719ef7bd69fa7*****2e2b0ed48f1765"
}
```

For the callback URL you will need to setup a webserver hosting `contrib/withings.html`.
