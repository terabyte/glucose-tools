#!/usr/bin/env python3

import argparse
import csv
import datetime
import dateutil
import json
import logging
import memoization
import os
import pprint
import sys

import matplotlib.pyplot as plt
import numpy as np

HEADER_ORDER = [
    'Device',
    'Serial Number',
    'Device Timestamp',
    'Record Type',
    'Historic Glucose mg/dL',
    'Scan Glucose mg/dL',
    'Non-numeric Rapid-Acting Insulin',
    'Rapid-Acting Insulin (units)',
    'Non-numeric Food',
    'Carbohydrates (grams)',
    'Carbohydrates (servings)',
    'Non-numeric Long-Acting Insulin',
    'Long-Acting Insulin (units)',
    'Notes',
    'Strip Glucose mg/dL',
    'Ketone mmol/L',
    'Meal Insulin (units)',
    'Correction Insulin (units)',
    'User Change Insulin (units)',
]

BUILT_IN_HEADERS = {
    'Device': 'device',
    'Serial Number': 'sn',
    'Device Timestamp': 'timestamp',
    'Record Type': 'type',
    'Historic Glucose mg/dL': 'historic_glucose',
    'Scan Glucose mg/dL': 'glucose',
    'Non-numeric Rapid-Acting Insulin': 'nnra_insulin',
    'Rapid-Acting Insulin (units)': 'rai_units',
    'Non-numeric Food': 'food',
    'Carbohydrates (grams)': 'carbs_g',
    'Carbohydrates (servings)': 'carbs_serv',
    'Non-numeric Long-Acting Insulin': 'nnla_insulin',
    'Long-Acting Insulin (units)': 'lai_units',
    'Notes': 'notes',
    'Strip Glucose mg/dL': 'strip_glucose',
    'Ketone mmol/L': 'ketone',
    'Meal Insulin (units)': 'meal_insulin',
    'Correction Insulin (units)': 'correction_insulin',
    'User Change Insulin (units)': 'user_change_insulin',
}

"""
Example row:
[{'carbs_g': '',
  'carbs_serv': '',
  'correction_insulin': '',
  'device': 'FreeStyle LibreLink',
  'food': '',
  'glucose': '',
  'historic_glucose': '98',
  'ketone': '',
  'lai_units': '',
  'meal_insulin': '',
  'nnla_insulin': '',
  'nnra_insulin': '',
  'notes': '',
  'rai_units': '',
  'sn': '1b2333b8-1234-4cde-abcd-1ab23cdefga4',
  'strip_glucose': '',
  'timestamp': '12-28-2021 06:40 PM',
  'type': '0',
  'user_change_insulin': ''}]
"""


def date_to_output(datetime):
    return datetime.strftime("%Y%m%d_%H%M%S")


def main(config):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger('matplotlib').setLevel(logging.INFO)

    logging.info(f"File to analyze: {sys.argv[1]}")

    time_data = []
    data = {}
    #config = {
    #    'target_min': 70,
    #    'target_max': 180,
    #    'time_in_tz_min': 80.0,
    #    'time_in_tz_max': 100.0,
    #    'time_in_tz_warn': 70.0,
    #    'weeks_start_on': 6,  # 6 = sunday
    #}

    # first parse any cgm data
    for filepath in config.cgm_data:
        logging.info(f"Reading in CGM data file {filepath}")
        with open(filepath) as f:
            created_by = f.readline()
            headers = f.readline().strip().split(",")
            csv_rows = csv.reader(f)
            for line in csv_rows:
                row = {}
                for header_idx in range(len(HEADER_ORDER)):
                    row[BUILT_IN_HEADERS[HEADER_ORDER[header_idx]]] = line[header_idx]
                row['datetime'] = dateutil.parser.parse(row['timestamp'])
                row['time'] = row['datetime'].timestamp()
                time_data.append(row['time'])
                data[row['time']] = row

    # parse any notes data
    for filepath in config.notes_data:
        logging.info(f"Reading in notes data file {filepath}")
        with open(filepath) as f:
            rawdata = json.load(f)
            notes_data = list(map(lambda x: dict(x, datetime=dateutil.parser.parse(x['date'])), rawdata))
            notes_data = list(map(lambda x: dict(x, timestamp=x['datetime'].timestamp()), notes_data))
            config.notes = notes_data


    # merge notes from CGM data into notes data
    for time, record in data.items():
        if record['notes'] is not None and len(record['notes']) > 0:
            dt = dateutil.parser.parse(record['timestamp'])
            note = dict()
            note['datetime'] = dt
            note['date'] = str(dt)
            note['timestamp'] = dt.timestamp()
            note['text'] = record['notes']
            config.notes.append(note)

    current_datetime = datetime.datetime.now()
    timestr = date_to_output(current_datetime)
    # TODO: move this into args code
    reports_dir = os.path.join(os.getcwd(), "reports", timestr)
    logging.info(f"Generating reports for {timestr}, will store to {reports_dir}")
    os.makedirs(reports_dir, exist_ok=True)

    config.reports_dir = reports_dir
    generate_weekly_reports(config, data)
    generate_all_time_glucose_plot(os.path.join(reports_dir, "all-time-glucose-graph.png"), config, data)
    generate_all_time_tz_plot(os.path.join(reports_dir, "all-time-tz-graph.png"), config, data)
    generate_weekly_tz_plot(os.path.join(reports_dir, "weekly-tz-graph.png"), config, data)
    sys.exit(0)


@memoization.cached
def calculate_time_glucose_transitions(time_a, glucose_a, target_glucose, time_b, glucose_b):
    """
    Calculates the approximate time between two points the glucose level hits a
    certain value via linear extrapolation.

    Precondition:  time_a must be before time_b, target_glucose must be between
    glucose a and glucose_b, or I shall not be held responsible for the
    results! =)

    # ### test code TODO: test this, but it works!
    time_a = datetime.datetime.now()
    time_b = time_a + datetime.timedelta(seconds=100)

    glucose_a = 100
    glucose_b = 200

    print(f"Result should be {time_a + datetime.timedelta(seconds=20)}: " + str(calculate_time_glucose_transitions(time_a, glucose_a, 120, time_b, glucose_b)))

    print(f"Result should be {time_a + datetime.timedelta(seconds=45)}: " + str(calculate_time_glucose_transitions(time_a, glucose_a, 145, time_b, glucose_b)))

    print(f"Result should be {time_a + datetime.timedelta(seconds=15)}: " + str(calculate_time_glucose_transitions(time_a, glucose_b, 185, time_b, glucose_a)))
    # ### end test code
    """

    glucose_range = glucose_b - glucose_a
    time_delta_to_transition = ((target_glucose - glucose_a) / (glucose_b - glucose_a)) * (time_b - time_a)
    return time_a + time_delta_to_transition


@memoization.cached
def calculate_glucose_between_two_times(time_a, glucose_a, target_time, time_b, glucose_b):
    """
    Calculates the approximate glucose at a given time between two data
    points via linear extrapolation.

    Precondition:  time_a must be before target_time, time_b must be after
    target_time, or I shall not be held responsible for the results! =)

    TODO: write these as tests?  It works!
    # #### TEST CODE
    time_a = datetime.datetime.now()
    time_b = time_a + datetime.timedelta(days=1)
    glucose_a = 100
    glucose_b = 200

    target_one = time_a + datetime.timedelta(hours=4)
    glucose_one = ((200.0-100) * (1.0/6))+100

    target_two = time_a + datetime.timedelta(hours=12)
    glucose_two = 150.0

    backwards_target_three = time_a + datetime.timedelta(hours=4)
    backwards_glucose_three = ((100.0-200) * (1.0/6))+200

    result = calculate_glucose_between_two_times(time_a, glucose_a, target_one, time_b, glucose_b)
    print(f"Expected result {glucose_one}, got {result}")

    result = calculate_glucose_between_two_times(time_a, glucose_a, target_two, time_b, glucose_b)
    print(f"Expected result {glucose_two}, got {result}")

    result = calculate_glucose_between_two_times(time_a, glucose_b, backwards_target_three, time_b, glucose_a)
    print(f"Expected result {backwards_glucose_three}, got {result}")
    # #### END TEST CODE

    """
    timedelta_before = target_time - time_a
    timedelta_after = time_b - target_time

    ratio_to_apply = timedelta_before / (timedelta_before + timedelta_after)
    return glucose_a + ((glucose_b - glucose_a) * ratio_to_apply)


def get_tz_state(tz_min, tz_max, glucose):
    """
    Returns -1 if below target zone, +1 if above, and 0 if inside target zone.
    """
    if glucose < tz_min:
        return -1
    if glucose > tz_max:
        return 1
    return 0


# TODO: the arguments to this are massive, is this a bad idea to memoize?
@memoization.cached
def calculate_time_in_target(tz_min, tz_max, time_data, glucose, start_date=None, end_date=None):
    """
    Calculates the ratio of time between start_date and end_date that was in
    the target zone. (i.e., values 0 to 1)

    If either start or end is omitted, uses the start or end of data, respectively.

    If there is no data for the given time, returns 0.

    The calculation is performed thusly: when point B is on the opposite side
    of the target zone immediately after point A, the transition time is
    calculated by calculating the slope of the line connecting those points
    then calculating where that line crosses the border of the zone.

    # ### TODO TEST CODE
    time_data, glucose = graphify_glucose_data(data)

    logging.debug("Calculating TZ data")

    start_date = datetime.datetime(year=2022, month=4, day=3)
    end_date = start_date+datetime.timedelta(days=7)
    time_in_tz = calculate_time_in_target(config['target_min'], config['target_max'], time_data, glucose, start_date, end_date)
    logging.debug(f"Time in target zone from {start_date} to {end_date} is {time_in_tz*100:.2f}")
    # ### END TEST CODE

    """
    # Find the start point and end point
    if start_date is None:
        start_date = time_data[0]
    if end_date is None:
        end_date = time_data[-1]

    # if there is no data, return 0
    if start_date > time_data[-1]:
        return 0
    if end_date < time_data[0]:
        return 0

    # if start date is before first data point, or after last data point, truncate range to our data.
    if start_date < time_data[0]:
        start_date = time_data[0]
    if end_date > time_data[-1]:
        end_date = time_data[-1]

    # we might be given a start/end time which falls between two data points.
    # If that happens, we need to calculate the state at that time using our
    # avg method.
    time_deltas_in_zone = []
    tz_state = None
    new_tz_state = None
    last_transition_date = start_date
    for i in range(len(time_data)):
        if start_date == time_data[i]:
            tz_state = get_tz_state(tz_min, tz_max, glucose[i])
            continue
        if start_date < time_data[i] and start_date > time_data[i - 1]:
            start_glucose = calculate_glucose_between_two_times(time_data[i - 1], glucose[i - 1], start_date, time_data[i], glucose[i])
            tz_state = get_tz_state(tz_min, tz_max, start_glucose)
            continue
        if tz_state is None:
            # haven't found start yet
            continue
        # we are now in the range of interest.  See if we are at the end?
        if end_date == time_data[i]:
            # if we are at the end, all that matters is that if we are in our
            # TZ, we need to count this stretch as a timedelta in the tz.
            if tz_state == 0:
                time_deltas_in_zone.append(end_date - last_transition_date)
                break
        if time_data[i] > end_date:
            if tz_state == 0:
                # we were in target zone, make sure we still are
                # we went past the end of the range, so let's calculate what the glucose was exactly at the end.
                end_glucose = calculate_glucose_between_two_times(time_data[i - 1], glucose[i - 1], end_date, time_data[i], glucose[i])
                new_tz_state = get_tz_state(tz_min, tz_max, end_glucose)
                if new_tz_state == 0:
                    # in the zone until the end
                    time_deltas_in_zone.append(end_date - last_transition_date)
                    break
            # else, we are not in tz, who cares if we are just starting being in the zone, it's right at the end.  we can probably drop that datapoint.
            break

        # ok, not at the end yet, detect a mid-range transition
        new_tz_state = get_tz_state(tz_min, tz_max, glucose[i])
        if new_tz_state != tz_state:
            # we have transitioned.  3 states, 6 possible transitions:
            # 1 to 0, 1 to -1, 0 to 1, 0 to -1, -1 to 0, -1 to 1.
            # BUG: for now, we will ignore transitions from -1 to 1 or 1 to -1
            # what we COULD do is linear extrapolate when you entered and left
            # the zone but frankly if you have holes in your data that big, big
            # enough to make that jump, you probably aren't going to get useful
            # data anyways.
            pair = (tz_state, new_tz_state)
            if pair == (-1, 1) or pair == (1, -1):
                # still outside tz, nothing to do
                continue
            if pair == (0, 1):
                # was in tz, left tz on top
                time_left_tz = calculate_time_glucose_transitions(time_data[i - 1], glucose[i - 1], tz_max, time_data[i], glucose[i])
                time_deltas_in_zone.append(time_left_tz - last_transition_date)
                last_transition_date = time_left_tz
                tz_state = new_tz_state
                continue
            if pair == (0, -1):
                # was in tz, left tz on bottom
                time_left_tz = calculate_time_glucose_transitions(time_data[i - 1], glucose[i - 1], tz_min, time_data[i], glucose[i])
                time_deltas_in_zone.append(time_left_tz - last_transition_date)
                last_transition_date = time_left_tz
                tz_state = new_tz_state
                continue
            if pair == (1, 0):
                # entered tz on top
                time_entered_tz = calculate_time_glucose_transitions(time_data[i - 1], glucose[i - 1], tz_max, time_data[i], glucose[i])
                last_transition_date = time_entered_tz
                tz_state = new_tz_state
                continue
            if pair == (-1, 0):
                # entered tz on bottom
                time_entered_tz = calculate_time_glucose_transitions(time_data[i - 1], glucose[i - 1], tz_min, time_data[i], glucose[i])
                last_transition_date = time_entered_tz
                tz_state = new_tz_state
                continue
    # ok, we have collected all the time deltas in the TZ.  Ratio in tz is now sum of all deltas over end - start.
    total_time_in_tz = sum(time_deltas_in_zone, datetime.timedelta())
    total_time_range = end_date - start_date
    ratio = total_time_in_tz / total_time_range
    logging.debug(f"Found {len(time_deltas_in_zone)} times in tz totalling {total_time_in_tz} out of {total_time_range} or {ratio*100:.2f}%")
    return ratio


def graphify_glucose_data(data, start_date=None, end_date=None):
    logging.debug("Graphifying glucose data set")
    if start_date:
        logging.debug(f"Limiting dataset to dates after {date_to_output(start_date)}")
    if end_date:
        logging.debug(f"Limiting dataset to dates before {date_to_output(end_date)}")

    time_data = []
    glucose = []
    for ts in sorted(data.keys()):
        # include all valid data in our range
        if start_date and data[ts]['datetime'] < start_date:
            # date is before start date
            continue
        if end_date and data[ts]['datetime'] > end_date:
            # date is after end date
            continue

        # prefer glucose if available, but most data will be historic glucose
        # becuase that is the column that the CGMs fill in.
        if data[ts]['glucose']:
            time_data.append(data[ts]['datetime'])
            glucose.append(int(data[ts]['glucose']))
            continue
        if data[ts]['historic_glucose']:
            time_data.append(data[ts]['datetime'])
            glucose.append(int(data[ts]['historic_glucose']))
            continue
        #logging.debug(f"Skipping timestamp {ts} because it has no glucose data")
    return (time_data, glucose)


def graphify_time_in_tz_data(config, data, start_date=None, end_date=None, interval=datetime.timedelta(days=1)):
    logging.debug("Graphifying time in tz data set")
    time_data, glucose = graphify_glucose_data(data, start_date, end_date)

    time_in_tz_x = []
    time_in_tz_y = []

    #tz_time = calculate_time_in_target(config['target_min'], config['target_max'], time_data, glucose)
    current_day = time_data[0]
    while current_day <= time_data[-1]:
        time_in_tz_x.append(current_day)
        time_in_tz_y.append(100.0*calculate_time_in_target(config.target_min, config.target_max, time_data, glucose, current_day, current_day + interval))
        current_day = current_day + interval
    return (time_in_tz_x, time_in_tz_y)


def generate_glucose_plot_from_data(output_file, title, config, time_data, glucose):
    # some calculations before we get started...
    # time in target for entire graph
    tz_time = calculate_time_in_target(config.target_min, config.target_max, time_data, glucose)
    # y_min = int(np.min(glucose) * 0.95)
    # y_max = int(np.max(glucose) * 1.05)
    # y_ticks = 20

    # To find list of valid params here: pprint.pprint(plt.rcParams.keys())
    with plt.rc_context({
        'axes.autolimit_mode': 'round_numbers',
        'figure.figsize': [20, 4],  # todo: extract this?
        'axes.xmargin': 0.001,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.1,
    }):

        fig, ax = plt.subplots()
        fig.suptitle(title + f" (time in target: {tz_time*100:.1f}%)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Blood Glucose Level (mg/dL)")
        ax.set_yticks(np.arange(30, 500, 20))
        fig.autofmt_xdate()

        ax.plot(time_data, glucose, 'k.-', label="Blood Glucose Level (mg/dL)")

        # draw target zone
        plt.axhline(y=config.target_min, color='green', linestyle='--')
        plt.axhline(y=config.target_max, color='red', linestyle='--')
        (xlim_min, xlim_max) = ax.get_xbound()
        (ylim_min, ylim_max) = ax.get_ybound()
        plt.fill((xlim_min, xlim_max, xlim_max, xlim_min), (config.target_min, config.target_min, config.target_max, config.target_max), 'palegreen')

        # draw labeled notes if present
        for note in config.notes:
            logging.info(f"Annotating datetime {note['datetime']} with text '{note['text']}'")
            ax.annotate(
                note['text'], (note['datetime'], ylim_min),
                xytext=(90, -20), textcoords='offset pixels',
                arrowprops=dict(facecolor='red', width=0.1, headwidth=4, headlength=4),
                fontsize=7,
                horizontalalignment='right', verticalalignment='top',
            )

        legend = ax.legend()
        plt.savefig(output_file)

def generate_time_in_tz_plot_from_data(output_file, title, config, time_data, time_in_tz):
    # some upfront calculations
    avg_tz_time = np.average(time_in_tz)  # this works because time_data is always equally spaced out

    # To find list of valid params here: pprint.pprint(plt.rcParams.keys())
    with plt.rc_context({
        'axes.autolimit_mode': 'round_numbers',
        'figure.figsize': [20, 4],  # todo: extract this?
        'axes.xmargin': 0.001,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.1,
    }):

        fig, ax = plt.subplots()
        fig.suptitle(title + f" (all-time average: {avg_tz_time:.1f}%)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Time in target zone (%)")
        ax.set_yticks(np.arange(0, 100, 5))
        fig.autofmt_xdate()

        ax.plot(time_data, time_in_tz, 'k.-', label="Time in target zone (%)")

        # draw target zone
        plt.axhline(y=config.time_in_tz_max, color='green', linestyle='--')
        plt.axhline(y=config.time_in_tz_min, color='orange', linestyle='--')
        plt.axhline(y=config.time_in_tz_warn, color='red', linestyle='--')
        (xlim_min, xlim_max) = ax.get_xbound()
        (ylim_min, ylim_max) = ax.get_ybound()
        plt.fill((xlim_min, xlim_max, xlim_max, xlim_min), (config.time_in_tz_min, config.time_in_tz_min, config.time_in_tz_max, config.time_in_tz_max), 'palegreen')
        plt.fill((xlim_min, xlim_max, xlim_max, xlim_min), (config.time_in_tz_warn, config.time_in_tz_warn, config.time_in_tz_min, config.time_in_tz_min), 'palegoldenrod')

        # draw labeled notes if present
        for note in config.notes:
            logging.info(f"Annotating datetime {note['datetime']} with text '{note['text']}'")
            ax.annotate(
                note['text'], (note['datetime'], ylim_min),
                xytext=(90, -20), textcoords='offset pixels',
                arrowprops=dict(facecolor='red', width=0.1, headwidth=4, headlength=4),
                fontsize=7,
                horizontalalignment='right', verticalalignment='top',
            )

        legend = ax.legend()
        plt.savefig(output_file)

def generate_weekly_reports(config, data):
    time_data, glucose = graphify_glucose_data(data)
    # find the starting day of the same week as the first data point
    # first, get the minimum time on the same day
    first_day = datetime.datetime.combine(time_data[0].date(), datetime.time().min)
    while first_day.weekday() != config.weeks_start_on:
        first_day = first_day - datetime.timedelta(days=1)

    # now, generate each week
    reports = []
    while first_day < time_data[-1]:
        daystr = date_to_output(first_day)
        logging.info("Generating graph for week starting {daystr}")
        output_file = os.path.join(config.reports_dir, f"{daystr}_weekly.png")
        reports.append(output_file)
        generate_one_week_report(output_file, f"Blood Glucose Levels for the week starting {daystr}", config, data, first_day)
        first_day = first_day + datetime.timedelta(weeks=1)

    # generate the index file
    # TODO: this should be extracted out and generate based on what files are
    # present so it can include all graphs.  For now we will hardcode the
    # graphs we care about.
    with open(os.path.join(config.reports_dir, "index.html"), 'w') as f:
        f.write("<html>")
        f.write("<head><title>Blood Glucose Reports</title></head>")
        f.write("<body>")
        f.write("\t<h1>All-Time Glucose Levels</h1>")
        f.write("<p>")
        f.write(f"<img src=\"all-time-glucose-graph.png\"/>")
        f.write("</p>")
        f.write("\t<h1>All-Time daily time spent in zone</h1>")
        f.write("<p>")
        f.write(f"<img src=\"all-time-tz-graph.png\"/>")
        f.write("</p>")
        f.write("\t<h1>All-Time weekly time spent in zone</h1>")
        f.write("<p>")
        f.write(f"<img src=\"weekly-tz-graph.png\"/>")
        f.write("</p>")
        f.write("\t<h1>Weekly Blood Glucose Reports</h1>")
        for report_file in reports:
            f.write("<p>")
            f.write(f"<img src=\"{os.path.split(report_file)[-1]}\"/>")
            f.write("</p>")
        f.write("</body>")
        f.write("</html>")


def generate_one_week_report(output_file, title, config, data, start_date):
    """
    Given the already-parsed data, and a starting date, generate a graph of the data for the week starting at the given date.
    """
    time_data, glucose = graphify_glucose_data(data, start_date=start_date, end_date=(start_date + datetime.timedelta(weeks=1)))
    generate_glucose_plot_from_data(output_file, title, config, time_data, glucose)


def generate_all_time_glucose_plot(output_file, config, data):
    """
    Given the already-parsed data, generate a graph of all time blood glucose levels.
    """
    # first, produce data we can easily plot
    time_data, glucose = graphify_glucose_data(data)
    generate_glucose_plot_from_data(output_file, "All-Time Blood Glucose Levels", config, time_data, glucose)


def generate_weekly_tz_plot(output_file, config, data):
    """
    Given the already-parsed data, generate a graph of weekly pct time in tz
    """
    # first, produce data we can easily plot
    time_data, tz_data = graphify_time_in_tz_data(config, data, None, None, datetime.timedelta(weeks=1))
    generate_time_in_tz_plot_from_data(output_file, "All-Time Weekly Percentage Time in Target Zone", config, time_data, tz_data)


def generate_all_time_tz_plot(output_file, config, data):
    """
    Given the already-parsed data, generate a graph of all time pct time in tz
    """
    # first, produce data we can easily plot
    time_data, tz_data = graphify_time_in_tz_data(config, data)
    generate_time_in_tz_plot_from_data(output_file, "All-Time Daily Percentage Time in Target Zone", config, time_data, tz_data)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--target-min',
            help='Minimum Target Zone for Blood Glucose Level (in mg/dL)',
            default=70,
    )

    ap.add_argument('--target-max',
            help='Maximum Target Zone for Blood Glucose Level (in mg/dL)',
            default=180,
    )
    ap.add_argument('--time-in-tz-min',
            help='Minimum expected time in target zone in percent (e.g. 80.0)',
            default=80.0,
    )
    ap.add_argument('--time-in-tz-max',
            help='Maximum expected time in target zone in percent (e.g. 100.0)',
            default=100.0,
    )
    ap.add_argument('--time-in-tz-warn',
            help='Second best minimum expected time in target zone in percent (e.g. 70.0)',
            default=70.0,
    )
    ap.add_argument('--weeks-start-on',
            help='Day of the week that weekly graphs start on (0=monday, 6=sunday)',
            default=6,
    )
    ap.add_argument('--notes-data',
            help='Notes/Labels to annotate graphs (in JSON format)',
            nargs='+',
    )

    required = ap.add_argument_group('required arguments')
    required.add_argument('--cgm-data',
            help='Continuous Glucose Monitoring (CGM) data file(s) (in libreview CSV format)',
            nargs='+',
    )

    config = ap.parse_args()

    main(config)
