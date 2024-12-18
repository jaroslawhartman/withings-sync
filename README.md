> [!CAUTION]
> This fork of the withings-sync project introduces breaking changes that users need to be aware of before upgrading or using it.
> These changes were made to enhance security and compatibility but may require modifications to your existing setup.
>
> - The container now runs without root privileges.
> - Dependencies, virtual envs, packaging is now done by Poetry.
> - This fork requires a recent version of Python, currently capped at >= python 3.12.
>
> Make sure to go over the updated readme and test these new changes thoroughly for your environment.
> Chances are quite high you will have to make changes to make this work again. 

# withings-sync

A tool for synchronisation of the Withings API to:

- Garmin Connect
- Trainer Road
- raw JSON output

## 1. Installation Instructions
### 1.1 Installation of withings-sync with pip
> This method installs the package asuming you have a working python and pip installation. It relies on an external scheduler (e.g., cron on the host operating system) to manage job execution.
<details>
  <summary>Expand to show installation steps.</summary>

  1. installing the package:
  ```bash
  $ pip install withings-sync
  ```

  2. obtaining Withings authorization:
  When running for a very first time, you need to obtain Withings authorization:
  ```bash
  $ withings-sync
  2024-12-01 01:29:02,601 - withings - ERROR - Can\'t read config file /home/youruser/.withings_user.json
  2024-12-01 01:29:02,602 - withings - WARNING - User interaction needed to get Authentification Code from Withings!
  2024-12-01 01:29:02,603 - withings - WARNING -
  2024-12-01 01:29:02,603 - withings - WARNING - Open the following URL in your web browser and copy back the token. You will have *30 seconds* before the token expires. HURRY UP!
  2024-12-01 01:29:02,603 - withings - WARNING - (This is one-time activity)
  2024-12-01 01:29:02,604 - withings - WARNING -
  2024-12-01 01:29:02,604 - withings - INFO - https://account.withings.com/oauth2_user/authorize2?response_type=code&client_id=183e03e1f363110b3551f96765c98c10e8f1aa647a37067a1cb64bbbaf491626&state=OK&scope=user.metrics&redirect_uri=https://jaroslawhartman.github.io/withings-sync/contrib/withings.html&
  2024-12-01 01:29:02,604 - withings - INFO -

  Token : <PASTE TOKEN>

  2024-12-01 01:31:07,832 - withings - INFO - Get Access Token
  2024-12-01 01:31:08,313 - withings - INFO - Refresh Access Token
  2024-12-01 01:31:08,771 - root - INFO - Fetching measurements from 2024-12-01 00:00 to 2024-12-01 23:59
  2024-12-01 01:31:09,406 - withings - INFO - Get Measurements
  2024-12-01 01:31:09,856 - root - ERROR - No measurements to upload for date or period specified
  ```
  You need to visit the URL listed by the script and then - copy Authentification Code back to the prompt.

  This is one-time activity and it will not be needed to repeat. 

  3. running the application:
  Subsequent runs will use the saved access tokens in `~/.withings_user.json`
  ```bash
  $ withings-sync
  2024-12-01 01:37:41,500 - withings - INFO - Refresh Access Token
  2024-12-01 01:37:41,954 - root - INFO - Fetching measurements from 2024-12-01 00:00 to 2024-12-01 23:59
  2024-12-01 01:37:42,563 - withings - INFO - Get Measurements
  2024-12-01 01:37:43,069 - root - ERROR - No measurements to upload for date or period specified
  ```
</details>

### 1.2 Installation of withings-sync with docker compose (not using cron)
> This method follows a default approach of utilizing a single container to run one job at a time, then exiting upon completion. It relies on an external scheduler (e.g., cron on the host operating system) to manage job execution.
<details>
  <summary>Expand to show installation steps.</summary>

  1. create the following file/directory structure:
  ```bash
  .                                          # STACK_PATH
  ./.env                                     # .env file containing your variables
  ./docker-compose.yml                       # docker-compose file
  ./config/                                  # config directory
  ./config/withings-sync/                    # config directory for withings-sync
  ./config/withings-sync/.withings_user.json # .withings_user.json file to store access tokens
  ./config/withings-sync/.garmin_session/    # .garmin_session directory to store oauth tokens
  ```

  2. contents of an example `.env` file:
  ```bash
  TZ=Europe/Kyiv
  STACK_PATH=/home/your_user/your_stack_name
  GARMIN_USERNAME="your.name@domain.ext"
  GARMIN_PASSWORD="YourPasswordHere"
  ```
  
  3. contents of an example `docker-compose.yml` file:
  ```yaml
  services:
    withings-sync:
      image: ghcr.io/jaroslawhartman/withings-sync:latest
      container_name: withings-sync
      stdin_open: true # docker run -i
      tty: true        # docker run -t
      environment:
        - TZ=${TZ:?err}
        - GARMIN_USERNAME=${GARMIN_USERNAME:?err}
        - GARMIN_PASSWORD=${GARMIN_PASSWORD:?err}
      volumes:
        - /etc/localtime:/etc/localtime:ro
        - ${STACK_PATH:?err}/config/withings-sync/.withings_user.json:/home/withings-sync/.withings_user.json
        - ${STACK_PATH:?err}/config/withings-sync/.garmin_session:/home/withings-sync/.garmin_session
      restart: unless-stopped
  ```

  4. obtaining Withings authorization:
  ```bash
  $ docker compose pull
  [+] Pulling 13/13
  ✔ withings-sync Pulled                                                           56.0s
    ✔ cb8611c9fe51 Pull complete                                                    4.2s
    ✔ 52e189a1282f Pull complete                                                    6.4s
    ✔ 95e68cb0cebc Pull complete                                                   19.0s
    ✔ c3ba8bc06a4d Pull complete                                                   19.3s
    ✔ fc2b9c85008a Pull complete                                                   21.6s
    ✔ 0376fca350d9 Pull complete                                                   21.7s
    ✔ 4f4fb700ef54 Pull complete                                                   21.9s
    ✔ c749d618f51d Pull complete                                                   43.0s
    ✔ 86d00088bd8d Pull complete                                                   43.2s
    ✔ 98dec7b84387 Pull complete                                                   52.8s
    ✔ 8825309bd8c2 Pull complete                                                   53.1s
    ✔ 7747652082d6 Pull complete                                                   53.3s
  ```

  First start to ensure the script can start successfully:

  ```bash
  $ docker compose run -it --remove-orphans --entrypoint "poetry run withings-sync" withings-sync
  [+] Creating 1/1
  ✔ Network stack_default  Created                                                  0.5s
  2024-12-01 01:29:02,601 - withings - ERROR - Can\'t read config file /home/youruser/.withings_user.json
  2024-12-01 01:29:02,602 - withings - WARNING - User interaction needed to get Authentification Code from Withings!
  2024-12-01 01:29:02,603 - withings - WARNING -
  2024-12-01 01:29:02,603 - withings - WARNING - Open the following URL in your web browser and copy back the token. You will have *30 seconds* before the token expires. HURRY UP!
  2024-12-01 01:29:02,603 - withings - WARNING - (This is one-time activity)
  2024-12-01 01:29:02,604 - withings - WARNING -
  2024-12-01 01:29:02,604 - withings - INFO - https://account.withings.com/oauth2_user/authorize2?response_type=code&client_id=183e03e1f363110b3551f96765c98c10e8f1aa647a37067a1cb64bbbaf491626&state=OK&scope=user.metrics&redirect_uri=https://jaroslawhartman.github.io/withings-sync/contrib/withings.html&
  2024-12-01 01:29:02,604 - withings - INFO -

  Token : <PASTE TOKEN>

  2024-12-01 01:31:07,832 - withings - INFO - Get Access Token
  2024-12-01 01:31:08,313 - withings - INFO - Refresh Access Token
  2024-12-01 01:31:08,771 - root - INFO - Fetching measurements from 2024-12-01 00:00 to 2024-12-01 23:59
  2024-12-01 01:31:09,406 - withings - INFO - Get Measurements
  2024-12-01 01:31:09,856 - root - ERROR - No measurements to upload for date or period specified
  ```
  You need to visit the URL listed by the script and then - copy Authentification Code back to the prompt.

  This is one-time activity and it will not be needed to repeat.

  5. running the container:
  Subsequent runs will use the saved access tokens in `~/.withings_user.json`

  ```bash
  $ docker compose run -it --remove-orphans withings-sync                           0.5s
  [+] Creating 1/1
  ✔ Container stack-withings-sync-run-3f24bc7ec7f9  Removed
  2024-12-01 01:37:41,500 - withings - INFO - Refresh Access Token
  2024-12-01 01:37:41,954 - root - INFO - Fetching measurements from 2024-12-01 00:00 to 2024-12-01 23:59
  2024-12-01 01:37:42,563 - withings - INFO - Get Measurements
  2024-12-01 01:37:43,069 - root - ERROR - No measurements to upload for date or period specified
  ```

  6. updating to a newer version:
  ```bash
  $ docker compose pull
  $ docker compose run -it --remove-orphans withings-sync
  ```

</details>

### 1.3 Installation of withings-sync with docker compose (using supercronic)
> This method leverages the included supercronic package for scheduling jobs directly within the container. This eliminates the need for an external scheduler, allowing the container to manage job execution independently.
<details>
  <summary>Expand to show installation steps.</summary>

  1. create the following file/directory structure:
  ```bash
  .                                          # STACK_PATH
  ./.env                                     # .env file containing your variables
  ./docker-compose.yml                       # docker-compose file
  ./config/                                  # config directory
  ./config/withings-sync/                    # config directory for withings-sync
  ./config/withings-sync/entrypoint.sh       # entrypoint.sh file containing your 
  ./config/withings-sync/.garmin_session/    # .garmin_session directory to store oauth tokens
  ```

  2. contents of an example `.env` file:
  ```bash
  TZ=Europe/Kyiv
  STACK_PATH=/home/youruser/withings-sync
  GARMIN_USERNAME="your.name@domain.ext"
  GARMIN_PASSWORD="YourPasswordHere"
  ```

  3. contents of an example `entrypoint.sh` file:
  ```bash
  #!/bin/sh
  echo "$(( $RANDOM % 59 +0 )) */3 * * * poetry run withings-sync --verbose --features BLOOD_PRESSURE" > /home/withings-sync/cronjob
  supercronic /home/withings-sync/cronjob
  ```
  
  4. contents of an example `docker-compose.yml` file:
  ```yaml
  services:
  withings-sync:
    image: ghcr.io/jaroslawhartman/withings-sync:latest
    container_name: withings-sync
    stdin_open: true # docker run -i
    tty: true        # docker run -t
    environment:
      - TZ=${TZ:?err}
      - GARMIN_USERNAME=${GARMIN_USERNAME:?err}
      - GARMIN_PASSWORD=${GARMIN_PASSWORD:?err}
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - ${STACK_PATH:?err}/config/withings-sync/.withings_user.json:/home/withings-sync/.withings_user.json
      - ${STACK_PATH:?err}/config/withings-sync/.garmin_session:/home/withings-sync/.garmin_session
      - ${STACK_PATH:?err}/config/withings-sync/entrypoint.sh:/home/withings-sync/entrypoint.sh
    entrypoint: "sh /home/withings-sync/entrypoint.sh"
    restart: unless-stopped
  ```

  5. obtaining Withings authorization:
  ```bash
  $ docker compose pull
  [+] Pulling 13/13
  ✔ withings-sync Pulled                                                           56.0s
    ✔ cb8611c9fe51 Pull complete                                                    4.2s
    ✔ 52e189a1282f Pull complete                                                    6.4s
    ✔ 95e68cb0cebc Pull complete                                                   19.0s
    ✔ c3ba8bc06a4d Pull complete                                                   19.3s
    ✔ fc2b9c85008a Pull complete                                                   21.6s
    ✔ 0376fca350d9 Pull complete                                                   21.7s
    ✔ 4f4fb700ef54 Pull complete                                                   21.9s
    ✔ c749d618f51d Pull complete                                                   43.0s
    ✔ 86d00088bd8d Pull complete                                                   43.2s
    ✔ 98dec7b84387 Pull complete                                                   52.8s
    ✔ 8825309bd8c2 Pull complete                                                   53.1s
    ✔ 7747652082d6 Pull complete                                                   53.3s
  ```

  First start to ensure the container can start successfully:

  ```bash
  $ docker compose run -it --remove-orphans --entrypoint "poetry run withings-sync" withings-sync
  [+] Creating 1/1
  ✔ Network stack_default  Created                                                  0.5s
  2024-12-01 01:29:02,601 - withings - ERROR - Can\'t read config file /home/youruser/.withings_user.json
  2024-12-01 01:29:02,602 - withings - WARNING - User interaction needed to get Authentification Code from Withings!
  2024-12-01 01:29:02,603 - withings - WARNING -
  2024-12-01 01:29:02,603 - withings - WARNING - Open the following URL in your web browser and copy back the token. You will have *30 seconds* before the token expires. HURRY UP!
  2024-12-01 01:29:02,603 - withings - WARNING - (This is one-time activity)
  2024-12-01 01:29:02,604 - withings - WARNING -
  2024-12-01 01:29:02,604 - withings - INFO - https://account.withings.com/oauth2_user/authorize2?response_type=code&client_id=183e03e1f363110b3551f96765c98c10e8f1aa647a37067a1cb64bbbaf491626&state=OK&scope=user.metrics&redirect_uri=https://jaroslawhartman.github.io/withings-sync/contrib/withings.html&
  2024-12-01 01:29:02,604 - withings - INFO -

  Token : <PASTE TOKEN>

  2024-12-01 01:31:07,832 - withings - INFO - Get Access Token
  2024-12-01 01:31:08,313 - withings - INFO - Refresh Access Token
  2024-12-01 01:31:08,771 - root - INFO - Fetching measurements from 2024-12-01 00:00 to 2024-12-01 23:59
  2024-12-01 01:31:09,406 - withings - INFO - Get Measurements
  2024-12-01 01:31:09,856 - root - ERROR - No measurements to upload for date or period specified
  ```

  6. running the container:
  And for subsequent runs we start docker compose and let the container run in the background.
  Subsequent runs will use the saved access tokens in `~/.withings_user.json`

  ```bash
  $ docker compose up -d --remove-orphans
  [+] Running 1/1
  ✔ Container withings-sync                         Started                         1.5s
  ```

  7. updating to a newer version:
  ```bash
  $ docker compose pull
  $ docker compose down
  $ docker compose up -d --remove-orphans
  $ docker image prune -f
  ```
</details>

## 2. Usage Instructions

```
usage: withings-sync [-h] [--version] [--garmin-username GARMIN_USERNAME] [--garmin-password GARMIN_PASSWORD] 
                     [--trainerroad-username TRAINERROAD_USERNAME] [--trainerroad-password TRAINERROAD_PASSWORD] 
		     [--fromdate DATE] [--todate DATE] [--to-fit] [--to-json] [--output BASENAME] [--no-upload]
                     [--features BLOOD_PRESSURE [BLOOD_PRESSURE ...]] [--verbose]

A tool for synchronisation of Withings (ex. Nokia Health Body) to Garmin Connect and Trainer Road or to provide a json string.

options:
  -h, --help            show this help message and exit
  --version, -V         show program's version number and exit
  --garmin-username GARMIN_USERNAME, --gu GARMIN_USERNAME
                        Username to log in to Garmin Connect.
  --garmin-password GARMIN_PASSWORD, --gp GARMIN_PASSWORD
                        Password to log in to Garmin Connect.
  --trainerroad-username TRAINERROAD_USERNAME, --tu TRAINERROAD_USERNAME
                        Username to log in to TrainerRoad.
  --trainerroad-password TRAINERROAD_PASSWORD, --tp TRAINERROAD_PASSWORD
                        Password to log in to TrainerRoad.
  --fromdate DATE, -f DATE
                        Date to start syncing from. Ex: 2023-12-20
  --todate DATE, -t DATE
                        Date for the last sync. Ex: 2023-12-30
  --to-fit, -F          Write output file in FIT format.
  --to-json, -J         Write output file in JSON format.
  --output BASENAME, -o BASENAME
                        Write downloaded measurements to file.
  --no-upload           Won't upload to Garmin Connect or TrainerRoad.
  --features BLOOD_PRESSURE [BLOOD_PRESSURE ...]
                        Enable Features like BLOOD_PRESSURE.
  --verbose, -v         Run verbosely.
```

## 3. Providing credentials
### 3.1 Providing credentials via environment variables

You can use the following environment variables for providing the Garmin and/or Trainerroad credentials:

- `GARMIN_USERNAME`
- `GARMIN_PASSWORD`
- `TRAINERROAD_USERNAME`
- `TRAINERROAD_PASSWORD`

The CLI also uses python-dotenv to populate the variables above. Therefore setting the environment variables
has the same effect as placing the variables in a `.env` file in the working directory.

### 3.2 Providing credentials via secrets files

You can also populate the following 'secrets' files to provide the Garmin and/or Trainerroad credentials:

- `/run/secrets/garmin_username`
- `/run/secrets/garmin_password`
- `/run/secrets/trainerroad_username`
- `/run/secrets/trainerroad_password`

Secrets are useful in an orchestrated container context — see the [Docker Swarm](https://docs.docker.com/engine/swarm/secrets/) or [Rancher](https://rancher.com/docs/rancher/v1.6/en/cattle/secrets/) docs for more information on how to securely inject secrets into a container.

### 3.3 Order of priority for credentials

In the case of credentials being available via multiple means (e.g. [environment variables](#providing-credentials-via-environment-variables) and [secrets files](#providing-credentials-via-secrets-files)), the order of resolution for determining which credentials to use is as follows, with later methods overriding credentials supplied by an earlier method:

1. Read secrets file(s)
2. Read environment variable(s), variables set explicitly take precedence over values from a `.env` file.
3. Use command invocation argument(s)

## 4. Obtaining Withings Authorization

When running for a very first time, you need to obtain Withings authorization:

### 4.1 'normal' shell:

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

### 4.2 Docker

```
$ docker pull ghcr.io/jaroslawhartman/withings-sync:latest
```

First start to ensure the script can start successfully:


Obtaining Withings authorisation:

```
$ docker run -v $HOME:/root --interactive --tty --name withings ghcr.io/jaroslawhartman/withings-sync:latest --garmin-username=<username> --garmin-password=<password>

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

## 5. Tips

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

### Garmin auth

You can configure the location of the garmin session file with the variabe `GARMIN_SESSION`.

### Run a periodic Kubernetes job

Edit the credentials in `contrib/k8s-job.yaml` and run:

```bash
$ kubectl apply -f contrib/k8s-job.yaml
```

### For advanced users - registering own Withings application
<details>
  <summary>If you are not sure you need this, you most likely won't.</summary>

The script has been registered as a Withings application and got assigned `Client ID` and `Consumer Secret`. If you wish to create your own application - feel free!


* First you need a Withings account. [Sign up here](https://account.withings.com/connectionuser/account_create).
* Then you need a Withings developer app registered. [Create your app here](https://account.withings.com/partner/add_oauth2).

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

To do this in a Docker installation, you can use the environment variable `WITHINGS_APP` to point to a mounted `withings_app.json`

Example docker-compose:
```
  withings-sync:
    container_name: withings-sync
    image: ghcr.io/jaroslawhartman/withings-sync:latest
    volumes:
      - "withings-sync:/root"
      - "/etc/localtime:/etc/localtime:ro"
    environment:
      WITHINGS_APP: /home/withings-sync/withings_app.json
(...)
```
You can then add the app-config in `withings-sync/withings_app.json`

</details>

## 6. Release

Release works via the GitHub [Draft a new Release](https://github.com/jaroslawhartman/withings-sync/releases/new) 
function.
The `version` key in `pyproject.toml` will be bumped automatically (Version will be written to pyproject.toml file).

### Docker Image

Container images are created automagically by GitHub Action and published 
to [ghcr](https://github.com/jaroslawhartman/withings-sync/pkgs/container/withings-sync).

### Pypi & GitHub

Will be conducted automatically within the Github-Release cycle.
This needs the permission on the [pypi-project](https://pypi.org/project/withings-sync/).
The python packages are added to the GitHub releases by a GitHub Action.

## 7. References

* SSO authorization derived from https://github.com/cpfair/tapiriik
* TrainerRoad API from https://github.com/stuwilkins/python-trainerroad

## 8. Credits / Authors

* Based on [withings-garmin](https://github.com/ikasamah/withings-garmin) by Masayuki Hamasaki, improved to support SSO authorization in Garmin Connect 2.
* Based on [withings-garmin-v2](https://github.com/jaroslawhartman/withings-garmin-v2) by Jarek Hartman, improved Python 3 compatability, code-style and setuptools packaging, Kubernetes and Docker support. 
