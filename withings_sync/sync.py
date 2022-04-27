"""This module syncs measurement data from Withings to Garmin a/o TrainerRoad."""
import argparse
import time
import sys
import os
import logging
import json

from datetime import date, datetime

from withings_sync.withings2 import WithingsAccount
from withings_sync.garmin import GarminConnect
from withings_sync.trainerroad import TrainerRoad
from withings_sync.fit import FitEncoder_Weight


try:
    with open("/run/secrets/garmin_username", encoding="utf-8") as secret:
        GARMIN_USERNAME = secret.read()
except OSError:
    GARMIN_USERNAME = ""

try:
    with open("/run/secrets/garmin_password", encoding="utf-8") as secret:
        GARMIN_PASSWORD = secret.read()
except OSError:
    GARMIN_PASSWORD = ""

if "GC_USERNAME" in os.environ:
    GARMIN_USERNAME = os.getenv("GARMIN_USERNAME")

if "GC_PASSWORD" in os.environ:
    GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")


try:
    with open("/run/secrets/trainerroad_username", encoding="utf-8") as secret:
        TRAINERROAD_USERNAME = secret.read()
except OSError:
    TRAINERROAD_USERNAME = ""

try:
    with open("/run/secrets/trainerroad_password", encoding="utf-8") as secret:
        TRAINERROAD_PASSWORD = secret.read()
except OSError:
    TRAINERROAD_PASSWORD = ""

if "TR_USERNAME" in os.environ:
    TRAINERROAD_USERNAME = os.getenv("TRAINERROAD_USERNAME")

if "TR_PASSWORD" in os.environ:
    TRAINERROAD_PASSWORD = os.getenv("TRAINERROAD_PASSWORD")


def get_args():
    """get command-line arguments"""
    parser = argparse.ArgumentParser(
        description=(
            "A tool for synchronisation of Withings "
            "(ex. Nokia Health Body) to Garmin Connect"
            " and Trainer Road or to provide a json string."
        )
    )

    def date_parser(date_string):
        return datetime.strptime(date_string, "%Y-%m-%d")

    parser.add_argument(
        "--garmin-username",
        "--gu",
        default=GARMIN_USERNAME,
        type=str,
        metavar="GARMIN_USERNAME",
        help="username to log in to Garmin Connect.",
    )
    parser.add_argument(
        "--garmin-password",
        "--gp",
        default=GARMIN_PASSWORD,
        type=str,
        metavar="GARMIN_PASSWORD",
        help="password to log in to Garmin Connect.",
    )

    parser.add_argument(
        "--trainerroad-username",
        "--tu",
        default=TRAINERROAD_USERNAME,
        type=str,
        metavar="TRAINERROAD_USERNAME",
        help="username to log in to TrainerRoad.",
    )
    parser.add_argument(
        "--trainerroad-password",
        "--tp",
        default=TRAINERROAD_PASSWORD,
        type=str,
        metavar="TRAINERROAD_PASSWORD",
        help="password to log in to TrainerRoad.",
    )

    parser.add_argument("--fromdate", "-f", type=date_parser, metavar="DATE")
    parser.add_argument(
        "--todate", "-t", type=date_parser, default=date.today(), metavar="DATE"
    )

    parser.add_argument(
        "--to-fit", "-F", action="store_true", help=("Write output file in FIT format.")
    )
    parser.add_argument(
        "--to-json",
        "-J",
        action="store_true",
        help=("Write output file in JSON format."),
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        metavar="BASENAME",
        help=("Write downloaded measurements to file."),
    )

    parser.add_argument(
        "--no-upload",
        action="store_true",
        help=("Won't upload to Garmin Connect or " "TrainerRoad."),
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Run verbosely")

    return parser.parse_args()


def sync():
    """Sync measurements from Withings to Garmin a/o TrainerRoad"""

    if ARGS.to_json:
        json_data = {}

    # Withings API
    withings = WithingsAccount()

    if not ARGS.fromdate:
        startdate = withings.getLastSync()
    else:
        startdate = int(time.mktime(ARGS.fromdate.timetuple()))

    enddate = int(time.mktime(ARGS.todate.timetuple())) + 86399
    logging.info(
        "Fetching measurements from %s to %s",
        time.strftime("%Y-%m-%d %H:%M", time.gmtime(startdate)),
        time.strftime("%Y-%m-%d %H:%M", time.gmtime(enddate)),
    )

    height = withings.getHeight()

    groups = withings.getMeasurements(startdate=startdate, enddate=enddate)

    # Only upload if there are measurement returned
    if groups is None or len(groups) == 0:
        logging.error("No measurements to upload for date or period specified")
        return -1

    # Save this sync so we don't re-download the same data again (if no range has been specified)
    if not ARGS.fromdate:
        withings.setLastSync()

    # Create FIT file
    logging.debug("Generating fit file...")
    fit = FitEncoder_Weight()
    fit.write_file_info()
    fit.write_file_creator()

    last_date_time = None
    last_weight = None

    for group in groups:
        # Get extra physical measurements
        date_time = group.get_datetime()
        weight = group.get_weight()
        fat_ratio = group.get_fat_ratio()
        muscle_mass = group.get_muscle_mass()
        hydration = group.get_hydration()
        bone_mass = group.get_bone_mass()
        pulse_wave_velocity = group.get_pulse_wave_velocity()
        heart_pulse = group.get_heart_pulse()
        raw_data = group.get_raw_data()

        logging.debug("%s Detected data: ", date_time)
        for dataentry in raw_data:
            logging.debug(dataentry)

        if height and weight:
            bmi = round(weight / pow(height, 2), 1)
        else:
            bmi = None

        if hydration and weight:
            percent_hydration = round(hydration * 100.0 / weight, 2)
        else:
            percent_hydration = None

        if ARGS.to_json:
            sdt = str(date_time)
            if sdt not in json_data:
                json_data[sdt] = {}
            for dataentry in raw_data:
                for k,jd in dataentry.json_dict().items():
                    json_data[sdt][k] = jd
            if bmi is not None:
                json_data[sdt]['BMI'] = { "Value": bmi, "Unit": "kg/m^2"}
            if percent_hydration is not None:
                json_data[sdt]['Percent_Hydration'] = { "Value": percent_hydration, "Unit": "%"}

        if weight is None:
            logging.debug(
                "This Withings metric contains no weight data.  Not syncing..."
            )
            continue

        fit.write_device_info(timestamp=date_time)
        fit.write_weight_scale(
            timestamp=date_time,
            weight=weight,
            percent_fat=fat_ratio,
            percent_hydration=percent_hydration,
            bone_mass=bone_mass,
            muscle_mass=muscle_mass,
            bmi=bmi,
        )

        logging.debug(
            "Record: %s weight=%s kg, "
            "fat_ratio=%s %%, "
            "muscle_mass=%s kg, "
            "hydration=%s %%, "
            "bone_mass=%s kg, "
            "bmi=%s",
            date_time,
            weight,
            fat_ratio,
            muscle_mass,
            hydration,
            bone_mass,
            bmi,
        )

        if last_date_time is None or date_time > last_date_time:
            last_date_time = date_time
            last_weight = weight

    fit.finish()

    if last_weight is None:
        logging.error("Invalid weight")
        return -1

    if ARGS.output is not None:
        if ARGS.to_fit:
            filename = ARGS.output + ".fit"
            logging.info("Writing file to %s.", filename)
            try:
                with open(filename, "wb") as fitfile:
                    fitfile.write(fit.getvalue())
            except OSError:
                logging.error("Unable to open output file!")
        if ARGS.to_json:
            filename = ARGS.output + ".json"
            logging.info("Writing file to %s.", filename)
            try:
                with open(filename, "w", encoding="utf-8") as jsonfile:
                    json.dump(json_data, jsonfile, indent=4)
            except OSError:
                logging.error("Unable to open output file!")

    if ARGS.no_upload:
        logging.info("Skipping upload")
        return 0

    # Upload to Trainer Road
    if ARGS.trainerroad_username:
        logging.info("Trainerroad username set -- attempting to sync")
        logging.info(" Last weight %s.", last_weight)
        logging.info(" Measured %s.", last_date_time)

        t_road = TrainerRoad(ARGS.trainerroad_username, ARGS.trainerroad_password)
        t_road.connect()

        logging.info("Current TrainerRoad weight: %s kg.", t_road.weight)
        logging.info("Updating TrainerRoad weight to %s kg.", last_weight)

        t_road.weight = round(last_weight, 1)
        t_road.disconnect()

        logging.info("TrainerRoad update done!")
    else:
        logging.info("No Trainerroad username or a new measurement " "- skipping sync")

    # Upload to Garmin Connect
    if ARGS.garmin_username:
        garmin = GarminConnect()
        session = garmin.login(ARGS.garmin_username, ARGS.garmin_password)
        logging.debug("attempting to upload fit file...")
        if garmin.upload_file(fit.getvalue(), session):
            logging.info("Fit file uploaded to Garmin Connect")
    else:
        logging.info("No Garmin username - skipping sync")
    return 0


ARGS = get_args()


def main():
    """Main"""
    logging.basicConfig(
        level=logging.DEBUG if ARGS.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    logging.debug("Script invoked with the following arguments: %s", ARGS)

    if sys.version_info < (3, 0):
        print("Sorry, requires Python3, not Python2.")
        sys.exit(1)

    sync()
