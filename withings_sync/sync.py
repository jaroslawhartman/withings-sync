"""This module syncs measurement data from Withings to Garmin a/o TrainerRoad."""
import argparse
import csv
import time
import sys
import os
import logging
import tempfile

from datetime import date, datetime

from withings_sync.withings2 import WithingsAccount
from withings_sync.garmin import GarminConnect
from withings_sync.trainerroad import TrainerRoad
from withings_sync.fit import FitEncoder_Weight


def get_args():
    """get command-line arguments"""
    parser = argparse.ArgumentParser(
        description=(
            "A tool for synchronisation of Withings "
            "(ex. Nokia Health Body) to Garmin Connect"
            " and Trainer Road."
        )
    )

    def date_parser(date_string):
        return datetime.strptime(date_string, "%Y-%m-%d")

    parser.add_argument(
        "--garmin-username",
        "--gu",
        default=os.environ.get("GARMIN_USERNAME"),
        type=str,
        metavar="GARMIN_USERNAME",
        help="username to login Garmin Connect.",
    )
    parser.add_argument(
        "--garmin-password",
        "--gp",
        default=os.environ.get("GARMIN_PASSWORD"),
        type=str,
        metavar="GARMIN_PASSWORD",
        help="password to login Garmin Connect.",
    )

    parser.add_argument(
        "--trainerroad-username",
        "--tu",
        default=os.environ.get("TRAINERROAD_USERNAME"),
        type=str,
        metavar="TRAINERROAD_USERNAME",
        help="username to login TrainerRoad.",
    )
    parser.add_argument(
        "--trainerroad-password",
        "--tp",
        default=os.environ.get("TRAINERROAD_PASSWORD"),
        type=str,
        metavar="TRAINERROAD_PASSWORD",
        help="username to login TrainerRoad.",
    )

    parser.add_argument(
        "--fromdate", "-f", type=date_parser, default=date.today(), metavar="DATE"
    )
    parser.add_argument(
        "--todate", "-t", type=date_parser, default=date.today(), metavar="DATE"
    )

    parser.add_argument(
        "--csv-weight-dir",
        "--cwd",
        default=os.environ.get("CSV_WEIGHT_DIR"),
        type=str,
        metavar="CSV_WEIGHT_DIR",
        help="Location where to store weight.csv, defaults to os tmp location.",
    )

    parser.add_argument(
        "--no-upload",
        action="store_true",
        help=("Won't upload to Garmin Connect and " "output binary-strings to stdout."),
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


def generate_fitfile(syncdata):
    """Generate fitfile from measured data"""
    # Create FIT file
    logging.debug("Generating fit file...")

    fit = FitEncoder_Weight()
    fit.write_file_info()
    fit.write_file_creator()

    for record in syncdata:
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
    return fit


def prepare_syncdata(height, groups, csv_fullpath):
    """Prepare measurement data to be sent"""
    syncdata = []

    last_date_time = None
    last_weight = None

    for group in groups:
        # Get extra physical measurements
        groupdata = {
            "date_time": group.get_datetime(),
            "height": height,
            "weight": group.get_weight(),
            "fat_ratio": group.get_fat_ratio(),
            "muscle_mass": group.get_muscle_mass(),
            "hydration": group.get_hydration(),
            "percent_hydration": None,
            "bone_mass": group.get_bone_mass(),
            "bmi": None,
        }
        raw_data = group.get_raw_data()

        if groupdata["weight"] is None:
            logging.info(
                "This Withings metric contains no weight data.  Not syncing..."
            )
            logging.debug("Detected data: ")
            for dataentry in raw_data:
                logging.debug(dataentry)
            continue
        if height:
            groupdata["bmi"] = round(
                groupdata["weight"] / pow(groupdata["height"], 2), 1
            )
        if groupdata["hydration"]:
            groupdata["percent_hydration"] = (
                groupdata["hydration"] * 100.0 / groupdata["weight"]
            )

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
        if last_date_time is None or groupdata["date_time"] > last_date_time:
            last_date_time = groupdata["date_time"]
            last_weight = groupdata["weight"]

    try:
        with open(csv_fullpath, "r", newline="", encoding="utf-8") as csvfile:
            reader = csvfile.read()
            if str(groupdata["date_time"]) not in reader:
                logging.debug(
                    "record for %s not found... adding...", groupdata["date_time"]
                )
                syncdata.append(groupdata)
            else:
                logging.debug(
                    "record for %s FOUND... skipping...", groupdata["date_time"]
                )
            csvfile.close()
    except FileNotFoundError:
        logging.debug(
            "%s: file not found... adding record for %s ...",
            csv_fullpath,
            groupdata["date_time"],
        )
        syncdata.append(groupdata)
    return last_weight, last_date_time, syncdata


def log2csv(csv_fullpath, syncdata):
    """function to add retrieved data to a local csv file"""
    try:
        with open(csv_fullpath, "r+", newline="", encoding="utf-8") as csvfile:
            csvfile.close()
    except FileNotFoundError:
        logging.debug("%s: file not found... creating...", csv_fullpath)
        with open(csv_fullpath, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Body"])
            writer.writerow(
                ["Date", "Weight", "BMI", "Fat", "Bone", "Hydration", "Muscle"]
            )
            csvfile.close()
    else:
        logging.debug("File %s found...  appending...", csv_fullpath)
    finally:
        with open(csv_fullpath, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            for data in syncdata:
                writer.writerow(
                    [
                        data["date_time"],
                        data["weight"],
                        data["bmi"],
                        data["fat_ratio"],
                        data["bone_mass"],
                        data["percent_hydration"],
                        data["muscle_mass"],
                    ]
                )
            csvfile.close()


def sync():
    """Sync measurements from Withings to Garmin a/o TrainerRoad"""

    trainerroad_sync_ok = False
    garmin_sync_ok = False

    csv_fullpath = ARGS.csv_weight_dir + "/" + "withings-sync-log.csv"

    # Withings API
    withings = WithingsAccount()
    height = withings.get_height()
    groups = withings.get_measurements(
        startdate=int(time.mktime(ARGS.fromdate.timetuple())),
        enddate=int(time.mktime(ARGS.todate.timetuple())) + 86399,
    )

    # Only upload if there are measurement returned
    if groups is None or len(groups) == 0:
        logging.error("No measurements to upload for date or period specified")
        return -1

    last_weight, last_date_time, syncdata = prepare_syncdata(
        height, groups, csv_fullpath
    )
    fitfile = generate_fitfile(syncdata)

    if last_weight is None:
        logging.error("Invalid weight")
        return -1

    if ARGS.no_upload:
        sys.stdout.buffer.write(fitfile.getvalue())
        return 0

    # Upload to Trainer Road
    if ARGS.trainerroad_username:
        logging.info("Trainerroad username set -- attempting to sync")
        logging.info(" Last weight %s", last_weight)
        logging.info(" Measured %s", last_date_time)
        if sync_trainerroad(last_weight):
            trainerroad_sync_ok = True
            logging.info("TrainerRoad update done!")
    else:
        logging.info("No Trainerroad username or a new measurement " "- skipping sync")

    # Upload to Garmin Connect
    if ARGS.garmin_username:
        logging.debug("attempting to upload fit file...")
        if sync_garmin(fitfile):
            garmin_sync_ok = True
            logging.info("Fit file uploaded to Garmin Connect")
    else:
        logging.info("No Garmin username - skipping sync")

    # Log to local csv file
    logging.debug("Attempting to save data to local file %s", csv_fullpath)
    if trainerroad_sync_ok or garmin_sync_ok:
        log2csv(csv_fullpath, syncdata)
        logging.info("Measurements saved to local csv file.")
    else:
        logging.debug(
            "No need to save to csv, Garmin nor Trainerroad sync was successfull."
        )
    return 0


ARGS = get_args()


def main():
    """Main"""
    logging.basicConfig(
        level=logging.DEBUG if ARGS.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.debug("Script invoked with the following arguments: %s", ARGS)

    if not ARGS.csv_weight_dir:
        ARGS.csv_weight_dir = tempfile.gettempdir()

    sync()
