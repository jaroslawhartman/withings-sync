# withings-garmin-v2

**NOTE: For Docker usage hits see at end of this document** https://hub.docker.com/r/jaroslawhartman/withings-garmin

**NOTE: Withings is a legacy name of Nokia Health Body / Body Cardio Scales. Feel free to use this script with Nokia products as well**

**NOTE: Included support for Withings OAuth2! See 'Obtaining Withings authorization'**


## References

* Based on withings-garmin by Masayuki Hamasaki, improved to support SSO authorization in Garmin Connect 2.

* SSO authorization derived from https://github.com/cpfair/tapiriik

## Pre-requisites

* Python 3
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

### Obtaining Withings Authorization Code

  
When running for a very first time, you need to obtain Withings authorization:

```
$ ./sync.py -f 2019-01-25 -v
Can't read config file config/withings_user.json
***************************************
*         W A R N I N G               *
***************************************

User interaction needed to get Authentification Code from Withings!

Open the following URL in your web browser and copy back the token. You will have *30 seconds* before the token expires. HURRY UP!
(This is one-time activity)

https://account.withings.com/oauth2_user/authorize2?response_type=code&client_id=183e03e1f363110b3551f96765c98c10e8f1aa647a37067a1cb64bbbaf491626&state=OK&scope=user.metrics&redirect_uri=https://wieloryb.uk.to/withings/withings.html&

Token :
```

You need to visit the URL listed by the script and then - copy Authentification Code back to the prompt.

This is one-time activity and it will not be needed to repeat.


## Tips

### Docker

```
$ docker pull jaroslawhartman/withings-garmin
```

First start to ensure the script can start successfully:

```
jhartman@docker:~/withings-garmin-v2/Docker$ docker run -it --rm --name withings jaroslawhartman/withings-garmin
Usage: sync.py [options]

Options:
  -h, --help            show this help message and exit
  --garmin-username=<user>, --gu=<user>
                        username to login Garmin Connect.
  --garmin-password=<pass>, --gp=<pass>
                        password to login Garmin Connect.
  -f <date>, --fromdate=<date>
  -t <date>, --todate=<date>
  --no-upload           Won't upload to Garmin Connect and output binary-
                        strings to stdout.
  -v, --verbose         Run verbosely
```

Obtaining Withings authoorisation:

```
$ docker run -it --name withings jaroslawhartman/withings-garmin --garmin-username=<username> --garmin-password=<password>

Can't read config file config/withings_user.json
***************************************
*         W A R N I N G               *
***************************************

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


### You can hardcode your usernames and passwords in the script (`sync.py`):

```
GARMIN_USERNAME = ''
GARMIN_PASSWORD = ''
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
