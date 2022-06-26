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

if "GARMIN_USERNAME" in os.environ:
    GARMIN_USERNAME = os.getenv("GARMIN_USERNAME")

if "GARMIN_PASSWORD" in os.environ:
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

if "TRAINERROAD_USERNAME" in os.environ:
    TRAINERROAD_USERNAME = os.getenv("TRAINERROAD_USERNAME")

if "TRAINERROAD_PASSWORD" in os.environ:
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


def sync_garmin(fit_file):
    """Sync generated fit file to Garmin Connect"""
    garmin = GarminConnect()
    session = garmin.login(ARGS.garmin_username, ARGS.garmin_password)
    return garmin.upload_file(fit_file.getvalue(), session)


def sync_trainerroad(last_weight):
    """Sync measured weight to TrainerRoad"""
    t_road = TrainerRoad(ARGS.trainerroad_username, ARGS.trainerroad_password)
    t_road.connect()
    logging.info("Current TrainerRoad weight: %s kg ", t_road.weight)
    logging.info("Updating TrainerRoad weight to %s kg", last_weight)
    t_road.weight = round(last_weight, 1)
    t_road.disconnect()
    return t_road.weight


def generate_fitdata(syncdata):
    """Generate fit data from measured data"""
    logging.debug("Generating fit data...")

    have_weight = False
    for record in syncdata:
        if "weight" in record:
            have_weight = True
            break
        next

    if not have_weight:
        logging.info("No weight data to sync for FIT file")
        return None

    fit = FitEncoder_Weight()
    fit.write_file_info()
    fit.write_file_creator()

    for record in syncdata:
        if "weight" not in record:
            next
        fit.write_device_info(timestamp=record["date_time"])
        fit.write_weight_scale(
            timestamp=record["date_time"],
            weight=record["weight"],
            percent_fat=record["fat_ratio"],
            percent_hydration=record["percent_hydration"],
            bone_mass=record["bone_mass"],
            muscle_mass=record["muscle_mass"],
            bmi=record["bmi"],
        )

    fit.finish()

    logging.debug("Fit data generated...")
    return fit


def generate_jsondata(syncdata):
    """Generate fit data from measured data"""
    logging.debug("Generating json data...")

    json_data = {}
    for record in syncdata:
        sdt = str(record["date_time"])
        json_data[sdt] = {}
        for dataentry in record["raw_data"]:
            for k,jd in dataentry.json_dict().items():
                json_data[sdt][k] = jd
        if "bmi" in record:
            json_data[sdt]["BMI"] = { "Value": record["bmi"], "Unit": "kg/m^2"}
        if "percent_hydration" in record:
             json_data[sdt]["Percent_Hydration"] = { "Value": record["percent_hydration"], "Unit": "%"}
    logging.debug("Json data generated...")
    return json_data


def prepare_syncdata(height, groups):
    """Prepare measurement data to be sent"""
    syncdata = []

    last_date_time = None
    last_weight = None

    syncDict = {}

    for group in groups:
        # Get extra physical measurements
        dt = group.get_datetime()
        if dt not in syncDict:
            syncDict[dt] = {}
        groupdata = {
            "date_time": group.get_datetime(),
            "height": height,
            "weight": group.get_weight(),
            "fat_ratio": group.get_fat_ratio(),
            "muscle_mass": group.get_muscle_mass(),
            "hydration": group.get_hydration(),
            "percent_hydration": None,
            "bone_mass": group.get_bone_mass(),
            "pulse_wave_velocity": group.get_pulse_wave_velocity(),
            "heart_pulse": group.get_heart_pulse(),
            "bmi": None,
            "raw_data": group.get_raw_data()
        }


        # if groupdata["weight"] is None:
            # logging.info(
            #    "This Withings metric contains no weight data.  Not syncing..."
            # )
            # logging.debug("Detected data: ")
            # continue
        if height and "weight" in groupdata:
            groupdata["bmi"] = round(
                groupdata["weight"] / pow(groupdata["height"], 2), 1
            )
        if groupdata["hydration"]:
            groupdata["percent_hydration"] = round(
                groupdata["hydration"] * 100.0 / groupdata["weight"], 2
            )

        logging.debug("%s Detected data: ", dt)
        #for dataentry in raw_data:
        for dataentry in groupdata["raw_data"]:
            logging.debug(dataentry)
       
        logging.debug(
            "Record: %s, height=%s m, "
            "weight=%s kg, "
            "fat_ratio=%s %%, "
            "muscle_mass=%s kg, "
            "percent_hydration=%s %%, "
            "bone_mass=%s kg, "
            "bmi=%s",
            groupdata["date_time"],
            groupdata["height"],
            groupdata["weight"],
            groupdata["fat_ratio"],
            groupdata["muscle_mass"],
            groupdata["percent_hydration"],
            groupdata["bone_mass"],
            groupdata["bmi"],
        )
       
        # join groups with same timestamp
        for k,v in groupdata.items():
            syncDict[dt][k] = v

    for groupdata in syncDict.values():
        syncdata.append(groupdata)
        logging.debug("Processed data: ")
        for k,v in groupdata.items():
            logging.debug(k, v)
        if last_date_time is None or groupdata["date_time"] > last_date_time:
            last_date_time = groupdata["date_time"]
            last_weight = groupdata["weight"]
            logging.debug("last_dt: %s last_weight: %s", last_date_time, last_weight)

    if last_weight is None:
        logging.error("Invalid or no weight data detected")

    return last_weight, last_date_time, syncdata


def write_to_file_when_needed(fit_data, json_data):
    """Write measurements to file when requested"""
    if ARGS.output is not None:
        if ARGS.to_fit and fit_data is not None:
            filename = ARGS.output + ".fit"
            logging.info("Writing fitfile to %s.", filename)
            try:
                with open(filename, "wb") as fitfile:
                    fitfile.write(fit_data.getvalue())
            except OSError:
                logging.error("Unable to open output fitfile!")
        if ARGS.to_json:
            filename = ARGS.output + ".json"
            logging.info("Writing jsonfile to %s.", filename)
            try:
                with open(filename, "w", encoding="utf-8") as jsonfile:
                    json.dump(json_data, jsonfile, indent=4)
            except OSError:
                logging.error("Unable to open output jsonfile!")


def sync():
    """Sync measurements from Withings to Garmin a/o TrainerRoad"""

    # Withings API
    withings = WithingsAccount()

    if not ARGS.fromdate:
        startdate = withings.get_lastsync()
    else:
        startdate = int(time.mktime(ARGS.fromdate.timetuple()))

    enddate = int(time.mktime(ARGS.todate.timetuple())) + 86399
    logging.info(
        "Fetching measurements from %s to %s",
        time.strftime("%Y-%m-%d %H:%M", time.gmtime(startdate)),
        time.strftime("%Y-%m-%d %H:%M", time.gmtime(enddate)),
    )

    height = withings.get_height()
    groups = withings.get_measurements(startdate=startdate, enddate=enddate)

    # Only upload if there are measurement returned
    if groups is None or len(groups) == 0:
        logging.error("No measurements to upload for date or period specified")
        return -1

    # Save this sync so we don't re-download the same data again (if no range has been specified)
    if not ARGS.fromdate:
        withings.set_lastsync()

    last_weight, last_date_time, syncdata = prepare_syncdata(height, groups)

    fit_data = generate_fitdata(syncdata)
    json_data = generate_jsondata(syncdata)

    write_to_file_when_needed(fit_data, json_data)

    if ARGS.no_upload:
        logging.info("Skipping upload")
        return 0

    # Upload to Trainer Road
    if ARGS.trainerroad_username and last_weight is not None:
        logging.info("Trainerroad username set -- attempting to sync")
        logging.info(" Last weight %s", last_weight)
        logging.info(" Measured %s", last_date_time)
        if sync_trainerroad(last_weight):
            logging.info("TrainerRoad update done!")
    else:
        logging.info("No Trainerroad username or a new measurement " "- skipping sync")

    # Upload to Garmin Connect
    if ARGS.garmin_username and fit_data is not None:
        logging.debug("attempting to upload fit file...")
        if sync_garmin(fit_data):
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
