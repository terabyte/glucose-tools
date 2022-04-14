#!/usr/bin/env python3

import csv
import datetime
import dateutil
import logging
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


def main():
    logging.info(f"File to analyze: {sys.argv[1]}")

    time_data = []
    data = {}
    config = {
        'target_min': 70,
        'target_max': 180,
        'weeks_start_on': 6,  # 6 = sunday
    }

    with open(sys.argv[1]) as f:
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

    current_datetime = datetime.datetime.now()
    timestr = date_to_output(current_datetime)
    reports_dir = os.path.join(os.getcwd(), "reports", timestr)
    logging.info(f"Generating reports for {timestr}, will store to {reports_dir}")
    os.makedirs(reports_dir, exist_ok=True)

    config['reports_dir'] = reports_dir
    generate_weekly_reports(config, data)
    generate_all_time_plot(os.path.join(reports_dir, "all-time-graph.png"), config, data)
    sys.exit(0)


def graphify_data(data, start_date=None, end_date=None):
    logging.debug("Graphifying data set")
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
        logging.debug(f"Skipping timestamp {ts} because it has no glucose data")
    return (time_data, glucose)


def generate_plot_from_data(output_file, title, config, time_data, glucose):
    # some calculations before we get started...
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
        fig.suptitle(title)
        ax.set_xlabel("Date")
        ax.set_ylabel("Blood Glucose Level (mg/dL)")
        ax.set_yticks(np.arange(30, 500, 20))
        fig.autofmt_xdate()

        ax.plot(time_data, glucose, 'k.-', label=["Blood Glucose Level (mg/dL)"])

        # draw target zone
        plt.axhline(y=config['target_min'], color='green', linestyle='--')
        plt.axhline(y=config['target_max'], color='red', linestyle='--')
        (xlim_min, xlim_max) = ax.get_xbound()
        plt.fill((xlim_min, xlim_max, xlim_max, xlim_min), (config['target_min'], config['target_min'], config['target_max'], config['target_max']), 'palegreen')

        legend = ax.legend()
        plt.savefig(output_file)


def generate_weekly_reports(config, data):
    time_data, glucose = graphify_data(data)
    # find the starting day of the same week as the first data point
    # first, get the minimum time on the same day
    first_day = datetime.datetime.combine(time_data[0].date(), datetime.time().min)
    while first_day.weekday() != config['weeks_start_on']:
        first_day = first_day - datetime.timedelta(days=1)

    # now, generate each week
    reports = []
    while first_day < time_data[-1]:
        daystr = date_to_output(first_day)
        logging.info("Generating graph for week starting {daystr}")
        output_file = os.path.join(config['reports_dir'], f"{daystr}_weekly.png")
        reports.append(output_file)
        generate_one_week_report(output_file, f"Blood Glucose Levels for the week starting {daystr}", config, data, first_day)
        first_day = first_day + datetime.timedelta(weeks=1)

    # generate the index file
    with open(os.path.join(config['reports_dir'], "index.html"), 'w') as f:
        f.write("<html>")
        f.write("<head><title>Weekly Blood Glucose Reports</title></head>")
        f.write("<body>")
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
    time_data, glucose = graphify_data(data, start_date=start_date, end_date=(start_date + datetime.timedelta(weeks=1)))
    generate_plot_from_data(output_file, title, config, time_data, glucose)


def generate_all_time_plot(output_file, config, data):
    """
    Given the already-parsed data, generate a graph of all time blood glucose levels.
    """
    # first, produce data we can easily plot
    time_data, glucose = graphify_data(data)
    generate_plot_from_data(output_file, "All-Time Blood Glucose Levels", config, time_data, glucose)


if __name__ == '__main__':
    main()
