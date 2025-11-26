> [!CAUTION]
> This Release introduces breaking changes that users need to be aware of before upgrading or using it.
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

  <ins>1. installing the package:</ins>

  ```bash
  $ pip install withings-sync
  ```

  <ins>2. obtaining Withings authorization:</ins>

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

  <ins>3. running the application:</ins>

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

  <ins>1. create the following file/directory structure:</ins>

  ```bash
  .                                          # STACK_PATH
  ./.env                                     # .env file containing your variables
  ./docker-compose.yml                       # docker-compose file
  ./config/                                  # config directory
  ./config/withings-sync/                    # config directory for withings-sync
  ./config/withings-sync/.withings_user.json # .withings_user.json file to store access tokens
  ```

  <ins>2. contents of an example `.env` file:</ins>

  ```bash
  TZ=Europe/Kyiv
  STACK_PATH=/home/your_user/your_stack_name
  GARMIN_USERNAME="your.name@domain.ext"
  GARMIN_PASSWORD="YourPasswordHere"
  ```
 
  <ins>3. contents of an example `docker-compose.yml` file:</ins>
 
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
      restart: unless-stopped
  ```

  <ins>4. obtaining Withings authorization:</ins>
 
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

  <ins>5. running the container:</ins>

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

  <ins>6. updating to a newer version:</ins>
 
  ```bash
  $ docker compose pull
  $ docker compose run -it --remove-orphans withings-sync
  ```

  <ins>7. persisting Garmin session files (optional):</ins>

  For the Docker version: The Garmin session (oauth1_token.json/oauth2_token.json) is not exposed outside of the docker container so the MFA garmin login isn't persisted. Suggest exposing/writing these files outside the container via a docker-compose.yml change and the creation of a garmin_session directory in the root withings-sync directory.

  **Potential solution:**
  
  1. Create `garmin_session` directory in withings-sync:
  ```bash
  mkdir -p garmin_session
  ```

  2. Add environment variable and volume in docker-compose.yml:
  ```yaml
  environment:
    - TZ=${TZ:?err}
    - GARMIN_USERNAME=${GARMIN_USERNAME:?err}
    - GARMIN_PASSWORD=${GARMIN_PASSWORD:?err}
    - GARMIN_SESSION=/home/withings-sync/garmin_session/.garmin_session/
  volumes:
    - /etc/localtime:/etc/localtime:ro
    - ${STACK_PATH:?err}/config/withings-sync/.withings_user.json:/home/withings-sync/.withings_user.json
    - ${STACK_PATH:?err}/garmin_session/:/home/withings-sync/garmin_session/
  ```

  **Note:** Using an extra directory level (`garmin_session/.garmin_session/`) prevents a FileNotFoundError that occurs when the `.garmin_session` directory exists but doesn't contain the expected OAuth files. This allows withings-sync to create the `.garmin_session` subdirectory automatically.

  This will ensure that Garmin session files persist across container restarts and you won't need to re-authenticate with MFA each time the container is recreated.
</details>

### 1.3 Installation of withings-sync with docker compose (using supercronic)
> This method leverages the included supercronic package for scheduling jobs directly within the container. This eliminates the need for an external scheduler, allowing the container to manage job execution independently.
<details>
  <summary>Expand to show installation steps.</summary>

  <ins>1. create the following file/directory structure:</ins>
 
  > Make sure to create the directories (`mkdir`) & files (`touch`) upfront or docker will create them as root.
  ```bash
  .                                          # STACK_PATH
  ./.env                                     # .env file containing your variables
  ./docker-compose.yml                       # docker-compose file
  ./config/                                  # config directory
  ./config/withings-sync/                    # config directory for withings-sync
  ./config/withings-sync/entrypoint.sh       # entrypoint.sh file containing your cmd & arguments
  ./config/withings-sync/.withings_user.json # .withings_user.json file to store access tokens
  ```

  <ins>2. contents of an example `.env` file:</ins>
 
  ```bash
  TZ=Europe/Kyiv
  STACK_PATH=/home/youruser/withings-sync
  GARMIN_USERNAME="your.name@domain.ext"
  GARMIN_PASSWORD="YourPasswordHere"
  ```

  <ins>3. contents of an example `entrypoint.sh` file:</ins>
 
  ```bash
  #!/bin/sh
  echo "$(( $RANDOM % 59 +0 )) */3 * * * * * poetry run withings-sync --features BLOOD_PRESSURE" > /home/withings-sync/cronjob
  supercronic -debug -passthrough-logs /home/withings-sync/cronjob
  ```
 
  <ins>4. contents of an example `docker-compose.yml` file:</ins>
 
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
      - ${STACK_PATH:?err}/config/withings-sync/entrypoint.sh:/home/withings-sync/entrypoint.sh
      - ${STACK_PATH:?err}/config/withings-sync/.withings_user.json:/home/withings-sync/.withings_user.json
    entrypoint: "sh /home/withings-sync/entrypoint.sh"
    restart: unless-stopped
  ```

  <ins>5. obtaining Withings authorization:</ins>
 
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

  <ins>6. running the container:</ins>

  And for subsequent runs we start docker compose and let the container run in the background.
  Subsequent runs will use the saved access tokens in `~/.withings_user.json`

  ```bash
  $ docker compose up -d --remove-orphans
  [+] Running 1/1
  ✔ Container withings-sync                         Started                         1.5s
  ```

  <ins>7. logging:</ins>

  ```bash
  $ docker compose logs withings-sync
  withings-sync  | WARN[2024-12-24T09:23:55+01:00] process reaping disabled, not pid 1
  withings-sync  | INFO[2024-12-24T09:23:55+01:00] read crontab: /home/withings-sync/cronjob
  withings-sync  | DEBU[2024-12-24T09:23:55+01:00] try parse (7 fields): '53 */3 * * * poetry run'
  withings-sync  | DEBU[2024-12-24T09:23:55+01:00] failed to parse (7 fields): '53 */3 * * * poetry run': failed: syntax error in day-of-week field: 'poetry'
  withings-sync  | DEBU[2024-12-24T09:23:55+01:00] try parse (6 fields): '53 */3 * * * poetry'
  withings-sync  | DEBU[2024-12-24T09:23:55+01:00] failed to parse (6 fields): '53 */3 * * * poetry': failed: syntax error in year field: 'poetry'
  withings-sync  | DEBU[2024-12-24T09:23:55+01:00] try parse (5 fields): '53 */3 * * *'
  withings-sync  | DEBU[2024-12-24T09:23:55+01:00] job will run next at 2024-12-24 09:53:00 +0100 CET  job.command="poetry run withings-sync --features BLOOD_PRESSURE" job.position=0 job.schedule="53 */3 * * *"
  withings-sync  | INFO[2024-12-24T09:53:00+01:00] starting                      iteration=0 job.command="poetry run withings-sync --features BLOOD_PRESSURE" job.position=0 job.schedule="53 */3 * * *"
  withings-sync  | 2024-12-24 09:53:29,177 - withings - INFO - Refresh Access Token
  withings-sync  | 2024-12-24 09:53:29,380 - root - INFO - Fetching measurements from 2024-12-22 18:52 to 2024-12-24 23:59
  withings-sync  | 2024-12-24 09:53:29,662 - withings - INFO - Get Measurements
  withings-sync  | 2024-12-24 09:53:29,866 - root - INFO - 2024-12-24 08:08:57 This Withings metric contains no weight data or blood pressure.  Not syncing...
  withings-sync  | 2024-12-24 09:53:29,868 - root - INFO - 2024-12-24 08:08:57 This Withings metric contains no weight data or blood pressure.  Not syncing...
  withings-sync  | 2024-12-24 09:53:29,870 - root - INFO - 2024-12-24 08:08:57 This Withings metric contains no weight data or blood pressure.  Not syncing...
  withings-sync  | 2024-12-24 09:53:29,878 - root - INFO - No blood pressure data to sync for FIT file
  withings-sync  | 2024-12-24 09:53:29,880 - root - INFO - No TrainerRoad username or a new measurement - skipping sync
  withings-sync  | 2024-12-24 09:53:33,665 - root - INFO - Fit file with weight information uploaded to Garmin Connect
  withings-sync  | 2024-12-24 09:53:33,666 - withings - INFO - Saving Last Sync
  withings-sync  | INFO[2024-12-24T09:53:34+01:00] job succeeded                 iteration=0 job.command="poetry run withings-sync --features BLOOD_PRESSURE" job.position=0 job.schedule="53 */3 * * *"
  withings-sync  | DEBU[2024-12-24T09:53:34+01:00] job will run next at 2024-12-24 12:53:00 +0100 CET  job.command="poetry run withings-sync --features BLOOD_PRESSURE" job.position=0 job.schedule="53 */3 * * *"
  ```

  <ins>8. updating to a newer version:</ins>
 
  ```bash
  $ docker compose pull
  $ docker compose down
  $ docker compose up -d --remove-orphans
  $ docker image prune -f
  ```

  <ins>9. persisting Garmin session files (optional):</ins>

  For the Docker version: The Garmin session (oauth1_token.json/oauth2_token.json) is not exposed outside of the docker container so the MFA garmin login isn't persisted. Suggest exposing/writing these files outside the container via a docker-compose.yml change and the creation of a garmin_session directory in the root withings-sync directory.

  **Potential solution:**
  
  1. Create `garmin_session` directory in withings-sync:
  ```bash
  mkdir -p garmin_session
  ```

  2. Add environment variable and volume in docker-compose.yml:
  ```yaml
  environment:
    - TZ=${TZ:?err}
    - GARMIN_USERNAME=${GARMIN_USERNAME:?err}
    - GARMIN_PASSWORD=${GARMIN_PASSWORD:?err}
    - GARMIN_SESSION=/home/withings-sync/garmin_session/.garmin_session/
  volumes:
    - /etc/localtime:/etc/localtime:ro
    - ${STACK_PATH:?err}/config/withings-sync/entrypoint.sh:/home/withings-sync/entrypoint.sh
    - ${STACK_PATH:?err}/config/withings-sync/.withings_user.json:/home/withings-sync/.withings_user.json
    - ${STACK_PATH:?err}/garmin_session/:/home/withings-sync/garmin_session/
  ```

  **Note:** Using an extra directory level (`garmin_session/.garmin_session/`) prevents a FileNotFoundError that occurs when the `.garmin_session` directory exists but doesn't contain the expected OAuth files. This allows withings-sync to create the `.garmin_session` subdirectory automatically.

  This will ensure that Garmin session files persist across container restarts and you won't need to re-authenticate with MFA each time the container is recreated.
</details>

### 1.4 Installation of withings-sync with docker (not compose)
> This method follows a default approach of utilizing a single container to run one job at a time, then exiting upon completion. It relies on an external scheduler (e.g., cron on the host operating system) to manage job execution.
<details>
  <summary>Expand to show installation steps.</summary>

```bash
$ docker pull ghcr.io/jaroslawhartman/withings-sync:latest
```

First start to ensure the script can start successfully:


Obtaining Withings authorisation:

```bash
$ docker run -v .withings_user.json:/home/withings-sync/.withings_user.json --interactive --tty --name withings-sync ghcr.io/jaroslawhartman/withings-sync:latest --garmin-username=<username> --garmin-password=<password>

Can't read config file config/withings_user.json
User interaction needed to get Authentification Code from Withings!

Open the following URL in your web browser and copy back the token. You will have *30 seconds* before the token expires. HURRY UP!
(This is one-time activity)

https://account.withings.com/oauth2_user/authorize2?response_type=code&client_id=183e03e1f363110b3551f96765c98c10e8f1aa647a37067a1cb64bbbaf491626&state=OK&scope=user.metrics&redirect_uri=https://jaroslawhartman.github.io/withings-sync/contrib/withings.html&

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

```bash
$ docker start -i withings-sync
Withings: Refresh Access Token
Withings: Get Measurements
   Measurements received
JaHa.WAW.PL
Garmin Connect User Name: JaHa.WAW.PL
Fit file uploaded to Garmin Connect
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
  --dump-raw, -R        Dump the raw Withings API JSON for the selected date range to a file. 
                        If --output is provided, the file will be named BASENAME.withings_raw.json. 
                        Otherwise, a default filename with the date range will be used.
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

## 4. Tips

### 4.1 Garmin SSO errors

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

### 4.2 Garmin auth

You can configure the location of the garmin session file with the variabe `GARMIN_SESSION`.

### 4.3 Run a periodic Kubernetes job

1. Create the secret using kubectl in the command line.
```
export GARMIN_USERNAME="user@username.com"
export GARMIN_PASSWORD="superPassword"
export TRAINERROAD_USERNAME: "name@name.com"
export TRAINERROAD_PASSWORD: "superPassword"
kubectl create secret generic withings-secret --from-literal=GARMIN_USERNAME=$GARMIN_USERNAME --from-literal=GARMIN_PASSWORD=$GARMIN_PASSWORD
--from-literal=TRAINERROAD_USERNAME=$TRAINERROAD_USERNAME --from-literal=TRAINERROAD_PASSWORD=$TRAINERROAD_PASSWORD
```

2. Create the PVC.
```
kubectl apply -f k8s-pvc.yaml
```

3. Run the bootstrap pod, which attaches to the PVC for storing credentials. 
```
kubectl apply -f k8s-bootstrap.yaml
```
The bootstrap pod stays on indefinitely to allow time for you to exec in, and 
generate the credentials.

4. Exec into the bootstrap pod, generate credentials and store them in the PVC.
```
kubectl exec -it bootstrap-withings-sync -- sh
```
From _within_ the bootstrap pod:
```
poetry run withings-sync --fromdate=<RECORDED_DATE>
```
It is important that this run includes a date that has a record, as a record is required for the program to attempt an upload to garmin in order to create the session files for garmin.
The command above will allow entering the withings token and the MFA code for garmin. 
After successful auth, move the credentials into the PVC
```
mv .withings_user.json /data
mv .garmin_session /data
```
5. Create the cron job. The command in the cron job always symlinks to the credentials in the PVC. Hence, future authentication updates will be persisted.
```
kubectl apply -f k8s-job.yaml
```

## 5 For advanced users - registering own Withings application
> Instead of using the provided Withings application tokens you can register your own app with Withings and use that one instead. 
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
