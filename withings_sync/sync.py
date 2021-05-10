"""This module syncs measurement data from Withings to Garmin a/o TrainerRoad."""
import argparse
import time
import sys
import os
import logging

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


def prepare_syncdata(height, groups):
    """Prepare measurement data to be sent"""
    # Create FIT file
    logging.debug("Generating fit file...")

    fit = FitEncoder_Weight()
    fit.write_file_info()
    fit.write_file_creator()

    last_date_time = None
    last_weight = None
    bmi = None
    percent_hydration = None

    for group in groups:
        # Get extra physical measurements
        date_time = group.get_datetime()
        weight = group.get_weight()
        fat_ratio = group.get_fat_ratio()
        muscle_mass = group.get_muscle_mass()
        hydration = group.get_hydration()
        bone_mass = group.get_bone_mass()
        raw_data = group.get_raw_data()

        if weight is None:
            logging.info(
                "This Withings metric contains no weight data.  Not syncing..."
            )
            logging.debug("Detected data: ")
            for dataentry in raw_data:
                logging.debug(dataentry)
            continue
        if height:
            bmi = round(weight / pow(height, 2), 1)
        if hydration:
            percent_hydration = hydration * 100.0 / weight

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
            "Record: %s, height=%s m, "
            "weight=%s kg, "
            "fat_ratio=%s %%, "
            "muscle_mass=%s kg, "
            "hydration=%s %%, "
            "bone_mass=%s kg, "
            "bmi=%s",
            date_time,
            height,
            weight,
            fat_ratio,
            muscle_mass,
            percent_hydration,
            bone_mass,
            bmi,
        )
        if last_date_time is None or date_time > last_date_time:
            last_date_time = date_time
            last_weight = weight

    fit.finish()
    return last_weight, last_date_time, fit


def sync():
    """Sync measurements from Withings to Garmin a/o TrainerRoad"""

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

    last_weight, last_date_time, fitfile = prepare_syncdata(height, groups)

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
            logging.info("TrainerRoad update done!")
    else:
        logging.info("No Trainerroad username or a new measurement " "- skipping sync")

    # Upload to Garmin Connect
    if ARGS.garmin_username:
        logging.debug("attempting to upload fit file...")
        if sync_garmin(fitfile):
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
    )
    logging.debug("Script invoked with the following arguments: %s", ARGS)
    sync()
