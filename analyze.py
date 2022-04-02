#!/usr/bin/env python3

import csv
import dateutil
import json
import logging
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
def main():
    print(f"File to analyze: {sys.argv[1]}")

    time = []
    data = {}
    config = {
        'target_min':70,
        'target_max':180,
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
            time.append(row['time'])
            data[row['time']] = row


    #pprint.pprint(data[time[1]])
    generate_all_time_plot(config, data)
    sys.exit(0)



def generate_all_time_plot(config, data):
    """
    Given the already-parsed data, generate a graph of all time blood glucose levels.
    """
    # first, produce data we can easily plot
    time = []
    glucose = []
    for ts in sorted(data.keys()):
        # include all valid data...
        # prefer glucose if available, but most data will be historic glucose
        # becuase that is the column that the CGMs fill in.
        if data[ts]['glucose']:
            time.append(data[ts]['datetime'])
            glucose.append(int(data[ts]['glucose']))
            continue
        if data[ts]['historic_glucose']:
            time.append(data[ts]['datetime'])
            glucose.append(int(data[ts]['historic_glucose']))
            continue
        logging.debug(f"Skipping timestamp {ts} because it has no glucose data")

    # some calculations before we get started...
    y_min = int(np.min(glucose)*0.95)
    y_max = int(np.max(glucose)*1.05)
    y_ticks = 20

    with plt.rc_context({
        'axes.autolimit_mode': 'round_numbers',
        'figure.figsize': [20, 4]
    }):

        #plt.axes(ylim=(y_min, y_max), yticks=(np.arange(y_min, y_max, y_ticks)))
        fig, ax = plt.subplots()
        fig.suptitle("All-Time Blood Glucose Levels")
        ax.set_xlabel("Date")
        ax.set_ylabel("Blood Glucose Level (mg/dL)")
        ax.set_yticks(np.arange(30, 500, 20))
        #ax.set_axes(ylim=(y_min, y_max))
        fig.autofmt_xdate()

        ax.plot(time, glucose, 'k.-', label=["Blood Glucose Level (mg/dL)"])

        # draw target zone
        plt.axhline(y=config['target_min'], color='green', linestyle='--')
        plt.axhline(y=config['target_max'], color='red', linestyle='--')
        (xlim_min, xlim_max) = ax.get_xbound()
        plt.fill((xlim_min, xlim_max, xlim_max, xlim_min), (config['target_min'], config['target_min'], config['target_max'], config['target_max']), 'palegreen')

        # size
        size_factor = 2
        plt.gcf().set_size_inches(size_factor * plt.gcf().get_size_inches())
        #  https://stackoverflow.com/questions/13515471/matplotlib-how-to-prevent-x-axis-labels-from-overlapping
        # set ticks reasonably
        # https://stackabuse.com/change-tick-frequency-in-matplotlib/
        #pprint.pprint([0, int(np.max(glucose)*1.05), 10])
        #plt.yticks(np.arange(y_min, y_max, y_ticks))
        

        legend = ax.legend()
        plt.savefig('out.png')



#    for i in sorted(data.keys()):
#        if data[i]['e'] == 0:
#            success_version.append(count)
#            success_data.append(data[i]['d'])
#        else:
#            fail_version.append(count)
#            fail_data.append(data[i]['d'])
#        count += 1
#
#    # generate graph
#    fig, ax = plt.subplots()
#    fig.suptitle("Duration of artifact upload against total versions")
#    ax.set_xlabel("number of versions")
#    ax.set_ylabel("duration in seconds")
#    ax.plot(success_version, success_data, 'go', label=["success duration"])
#    ax.plot(fail_version, fail_data, 'rx', label=["failure duration"])
#    legend = ax.legend()
#    plt.gcf().set_size_inches(size_factor * plt.gcf().get_size_inches())
#    plt.savefig('out.png')
#
#    sys.exit(0)
#
#
if __name__ == '__main__':
    main()
