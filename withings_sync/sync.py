"""This module syncs measurement data from Withings to Garmin a/o TrainerRoad."""
import argparse
import time
import sys
import os
import logging
import json
import dotenv

from datetime import date, datetime
from importlib.metadata import version

# Load the environment variables from a .env (dotenv) file.
# This is done prior to importing other modules such that all variables,
# also the ones accessed in those modules, can be set in the dotenv file.
dotenv.load_dotenv()

from withings_sync.withings2 import WithingsAccount
from withings_sync.garmin import GarminConnect
from withings_sync.trainerroad import TrainerRoad
from withings_sync.fit import FitEncoderWeight, FitEncoderBloodPressure


def load_variable(env_var, secrets_file):
    """Load a variable from an environment variable or from a secrets file"""
    # Try to read the value from the secrets file. Silently fail if the file
    # cannot be read and use an empty value
    try:
        with open(secrets_file, encoding='utf-8') as secret:
            value = secret.read().strip("\n")
    except OSError:
        value = ""

    # Load variable from environment if it exists, otherwise use the
    # value read from the secrets file.
    return os.getenv(env_var, value)


GARMIN_USERNAME = load_variable('GARMIN_USERNAME', "/run/secrets/garmin_username")
GARMIN_PASSWORD = load_variable('GARMIN_PASSWORD', "/run/secrets/garmin_password")
TRAINERROAD_USERNAME = load_variable('TRAINERROAD_USERNAME', "/run/secrets/trainerroad_username")
TRAINERROAD_PASSWORD = load_variable('TRAINERROAD_PASSWORD', "/run/secrets/trainerroad_password")



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
        help="Username to log in to Garmin Connect.",
    )
    parser.add_argument(
        "--garmin-password",
        "--gp",
        default=GARMIN_PASSWORD,
        type=str,
        metavar="GARMIN_PASSWORD",
        help="Password to log in to Garmin Connect.",
    )

    parser.add_argument(
        "--trainerroad-username",
        "--tu",
        default=TRAINERROAD_USERNAME,
        type=str,
        metavar="TRAINERROAD_USERNAME",
        help="Username to log in to TrainerRoad.",
    )

    parser.add_argument(
        "--trainerroad-password",
        "--tp",
        default=TRAINERROAD_PASSWORD,
        type=str,
        metavar="TRAINERROAD_PASSWORD",
        help="Password to log in to TrainerRoad.",
    )

    parser.add_argument(
        "--fromdate", "-f",
        type=date_parser,
        metavar="DATE",
        help="Date to start syncing from. Ex: 2023-12-20",
    )

    parser.add_argument(
        "--todate", "-t",
        type=date_parser,
        default=date.today(),
        metavar="DATE",
        help="Date for the last sync. Ex: 2023-12-30",
    )

    parser.add_argument(
        "--to-fit", "-F",
        action="store_true",
        help="Write output file in FIT format.",
    )

    parser.add_argument(
        "--to-json",
        "-J",
        action="store_true",
        help="Write output file in JSON format.",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        metavar="BASENAME",
        help="Write downloaded measurements to file.",
    )

    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Won't upload to Garmin Connect or TrainerRoad.",
    )

    parser.add_argument(
        "--features",
        nargs='+',
        default=[],
        metavar="BLOOD_PRESSURE",
        help="Enable Features like BLOOD_PRESSURE."
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Run verbosely."
    )

    return parser.parse_args()


def sync_garmin(fit_file):
    """Sync generated fit file to Garmin Connect"""
    garmin = GarminConnect()
    garmin.login(ARGS.garmin_username, ARGS.garmin_password)
    return garmin.upload_file(fit_file)


def sync_trainerroad(last_weight):
    """Sync measured weight to TrainerRoad"""
    t_road = TrainerRoad(ARGS.trainerroad_username, ARGS.trainerroad_password)
    t_road.connect()
    logging.info("Current TrainerRoad weight: %s kg ", t_road.weight)
    logging.info("Updating TrainerRoad weight to %s kg", last_weight)
    wt = round(last_weight, 1)
    t_road.weight = wt
    t_road.disconnect()

    return wt


def generate_fitdata(syncdata):
    """Generate fit data from measured data"""
    logging.debug("Generating fit data...")

    weight_measurements = list(filter(lambda x: (x["type"] == "weight"), syncdata))
    blood_pressure_measurements = list(filter(lambda x: (x["type"] == "blood_pressure"), syncdata))

    fit_weight = None
    fit_blood_pressure = None

    if len(weight_measurements) > 0:
        fit_weight = FitEncoderWeight()
        fit_weight.write_file_info()
        fit_weight.write_file_creator()

        for record in weight_measurements:
            fit_weight.write_device_info(timestamp=record["date_time"])
            fit_weight.write_weight_scale(
                timestamp=record["date_time"],
                weight=record["weight"],
                percent_fat=record["fat_ratio"],
                percent_hydration=record["percent_hydration"],
                bone_mass=record["bone_mass"],
                muscle_mass=record["muscle_mass"],
                bmi=record["bmi"],
            )

        fit_weight.finish()
    else:
        logging.info("No weight data to sync for FIT file")

    if len(blood_pressure_measurements) > 0:
        fit_blood_pressure = FitEncoderBloodPressure()
        fit_blood_pressure.write_file_info()
        fit_blood_pressure.write_file_creator()

        for record in blood_pressure_measurements:
            fit_blood_pressure.write_device_info(timestamp=record["date_time"])
            fit_blood_pressure.write_blood_pressure(
                timestamp=record["date_time"],
                diastolic_blood_pressure=record["diastolic_blood_pressure"],
                systolic_blood_pressure=record["systolic_blood_pressure"],
                heart_rate=record["heart_pulse"],
            )

        fit_blood_pressure.finish()
    else:
        logging.info("No blood pressure data to sync for FIT file")

    logging.debug("Fit data generated...")
    return fit_weight, fit_blood_pressure


def generate_jsondata(syncdata):
    """Generate fit data from measured data"""
    logging.debug("Generating json data...")

    json_data = {}
    for record in syncdata:
        sdt = str(record["date_time"])
        json_data[sdt] = {}
        for dataentry in record["raw_data"]:
            for k, jd in dataentry.json_dict().items():
                json_data[sdt][k] = jd
        if "bmi" in record:
            json_data[sdt]["BMI"] = {"Value": record["bmi"], "Unit": "kg/m^2"}
        if "percent_hydration" in record:
            json_data[sdt]["Percent_Hydration"] = {"Value": record["percent_hydration"], "Unit": "%"}
    logging.debug("Json data generated...")
    return json_data


def prepare_syncdata(height, groups):
    """Prepare measurement data to be sent"""
    syncdata = []

    last_date_time = None
    last_weight = None

    sync_dict = {}

    for group in groups:
        # Get extra physical measurements
        dt = group.get_datetime()
        # create a default group_data
        group_data = {
            "date_time": group.get_datetime(),
            "type": "None",
            "raw_data": group.get_raw_data(),
        }

        if dt not in sync_dict:
            sync_dict[dt] = {}

        if group.get_weight():
            group_data = {
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
                "raw_data": group.get_raw_data(),
                "type": "weight",
            }
        elif group.get_diastolic_blood_pressure():
            group_data = {
                "date_time": group.get_datetime(),
                "diastolic_blood_pressure": group.get_diastolic_blood_pressure(),
                "systolic_blood_pressure": group.get_systolic_blood_pressure(),
                "heart_pulse": group.get_heart_pulse(),
                "raw_data": group.get_raw_data(),
                "type": "blood_pressure"
            }

        # execute the code below, if this is not a whitelisted entry like weight and blood pressure
        if "weight" not in group_data and not (
                "diastolic_blood_pressure" in group_data and "BLOOD_PRESSURE" in ARGS.features):
            collected_metrics = "weight data"
            if "BLOOD_PRESSURE" in ARGS.features:
                collected_metrics += " or blood pressure"
            elif "diastolic_blood_pressure" in group_data:
                collected_metrics += ", but blood pressure (to enable sync set --features BLOOD_PRESSURE)"


            logging.info(
                "%s This Withings metric contains no %s.  Not syncing...", dt, collected_metrics
            )
            groupdata_log_raw_data(group_data)
            # for now, remove the entry as we're handling only weight and feature enabled data
            del sync_dict[dt]
            continue

        if height and "weight" in group_data:
            group_data["bmi"] = round(
                group_data["weight"] / pow(group_data["height"], 2), 1
            )
        if "hydration" in group_data and group_data["hydration"]:
            group_data["percent_hydration"] = round(
                group_data["hydration"] * 100.0 / group_data["weight"], 2
            )

        logging.debug("%s Detected data: ", dt)
        groupdata_log_raw_data(group_data)
        if "weight" in group_data:
            logging.debug(
                "Record: %s, type=%s\n"
                "height=%s m, "
                "weight=%s kg, "
                "fat_ratio=%s %%, "
                "muscle_mass=%s kg, "
                "percent_hydration=%s %%, "
                "bone_mass=%s kg, "
                "bmi=%s",
                group_data["date_time"],
                group_data["type"],
                group_data["height"],
                group_data["weight"],
                group_data["fat_ratio"],
                group_data["muscle_mass"],
                group_data["percent_hydration"],
                group_data["bone_mass"],
                group_data["bmi"],
            )
        if "diastolic_blood_pressure" in group_data:
            logging.debug(
                "Record: %s, type=%s\n"
                "diastolic_blood_pressure=%s mmHg, "
                "systolic_blood_pressure=%s mmHg, "
                "heart_pulse=%s BPM, ",
                group_data["date_time"],
                group_data["type"],
                group_data["diastolic_blood_pressure"],
                group_data["systolic_blood_pressure"],
                group_data["heart_pulse"],
            )

        # join groups with same timestamp
        for k, v in group_data.items():
            sync_dict[dt][k] = v

    last_measurement_type = None

    for group_data in sync_dict.values():
        syncdata.append(group_data)
        logging.debug("Processed data: ")
        for k, v in group_data.items():
            logging.debug("%s=%s", k, v)
        if last_date_time is None or group_data["date_time"] > last_date_time:
            last_date_time = group_data["date_time"]
            last_measurement_type = group_data["type"]
            logging.debug("last_dt: %s last_weight: %s", last_date_time, last_weight)

    if last_measurement_type is None:
        logging.error("Invalid or no data detected")

    return last_measurement_type, last_date_time, syncdata


def groupdata_log_raw_data(groupdata):
    for dataentry in groupdata["raw_data"]:
        logging.debug("%s", dataentry)


def write_to_fitfile(filename, fit_data):
    logging.info("Writing fitfile to %s.", filename)
    try:
        with open(filename, "wb") as fitfile:
            fitfile.write(fit_data.getvalue())
    except OSError:
        logging.error("Unable to open output fitfile! %s", filename)


def write_to_file_when_needed(fit_data_weigth, fit_data_blood_pressure, json_data):
    """Write measurements to file when requested"""
    if ARGS.output is not None:
        if ARGS.to_fit:
            if fit_data_weigth is not None:
                write_to_fitfile(ARGS.output + ".weight.fit", fit_data_weigth)
            if fit_data_blood_pressure is not None:
                write_to_fitfile(ARGS.output + ".blood_pressure.fit", fit_data_blood_pressure)

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
        time.strftime("%Y-%m-%d %H:%M", time.localtime(startdate)),
        time.strftime("%Y-%m-%d %H:%M", time.localtime(enddate)),
    )

    height = withings.get_height()
    groups = withings.get_measurements(startdate=startdate, enddate=enddate)

    # Only upload if there are measurement returned
    if groups is None or len(groups) == 0:
        logging.error("No measurements to upload for date or period specified")
        return -1

    last_measurement_type, last_date_time, syncdata = prepare_syncdata(height, groups)

    fit_data_weight, fit_data_blood_pressure = generate_fitdata(syncdata)
    json_data = generate_jsondata(syncdata)

    write_to_file_when_needed(fit_data_weight, fit_data_blood_pressure, json_data)

    if not ARGS.no_upload:
        # get weight entries (in case of only blood_pressure)
        only_weight_entries = list(filter(lambda x: (x["type"] == "weight"), syncdata))
        last_weight_exists = len(only_weight_entries) > 0
        # Upload to Trainer Road
        if ARGS.trainerroad_username and last_weight_exists:
            # sort and get last weight
            last_weight_measurement = sorted(only_weight_entries, key=lambda x: x["date_time"])[-1]
            last_weight = last_weight_measurement["weight"]
            logging.info("Trainerroad username set -- attempting to sync")
            logging.info(" Last weight %s", last_weight)
            logging.info(" Measured %s", last_date_time)
            if sync_trainerroad(last_weight):
                logging.info("TrainerRoad update done!")
        else:
            logging.info("No TrainerRoad username or a new measurement " "- skipping sync")

        # Upload to Garmin Connect
        if ARGS.garmin_username and (
            fit_data_weight is not None or fit_data_blood_pressure is not None
        ):
            logging.debug("attempting to upload fit file...")
            gar_wg_state = None
            gar_bp_state = None
            if fit_data_weight is not None:
                gar_wg_state = sync_garmin(fit_data_weight)
                if gar_wg_state:
                    logging.info(
                        "Fit file with weight information uploaded to Garmin Connect"
                    )
            if fit_data_blood_pressure is not None:
                gar_bp_state = sync_garmin(fit_data_blood_pressure)
                if gar_bp_state:
                    logging.info(
                        "Fit file with blood pressure information uploaded to Garmin Connect"
                    )
            if gar_wg_state or gar_bp_state:
                # Save this sync so we don't re-download the same data again (if no range has been specified)
                if not ARGS.fromdate:
                    withings.set_lastsync()
        elif ARGS.garmin_username is None:
            logging.info("No Garmin username - skipping sync")
        else:
            logging.info("No Garmin data selected - skipping sync")
    else:
        logging.info("Skipping upload")
    return 0


ARGS = get_args()


def main():
    """Main"""
    logging.basicConfig(
        level=logging.DEBUG if ARGS.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    logging.debug("withings-sync script version %s", version("withings-sync"))
    logging.debug("Script invoked with the following arguments: %s", ARGS)

    if sys.version_info < (3, 7):
        print("Sorry, requires at least Python3.7 to avoid issues with SSL.")
        sys.exit(1)

    sync()

