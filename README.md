# Glucose Monitoring Tools

This tool reads in data taken from the Freestyle Libre glucose monitor, aggregates it, then generates graphs and does analysis or whatever.

# How to Use

```
# only tested with python3+
$ pyenv virtualenv glucose
$ pyenv local glucose
$ pip install -r requirements.txt
$ ./analyze.py --cgm-data path/to/data.csv
```
Optionally, you can specify --notes-data as well.  Here is an example of the file format:
[
    {"type":"label","date":"Sat 04 Dec 2021 12:00:00 AM PST","text":"Started 2000mg Metformin"},
    {"type":"label","date":"Thu 20 Jan 2022 12:00:00 AM PST","text":"Switched to 2000mg Metformin XR"},
    {"type":"label","date":"Fri 04 Mar 2022 12:00:00 AM PST","text":"Started 1mg Glimepiride"},
    {"type":"label","date":"Fri 15 Apr 2022 12:00:00 AM PDT","text":"Was sick for over a week"}
]

Currently, only type 'label' is supported, and those labels will be added to any graph that includes that time.

# TODO
* make index.html include all generated graphs
* include tags for labels so graphs can include only labels with a given tag
* % data completion - measure gaps in data?
* tag data points and apply colors? green if surrounding 24hrs is >80% in target?
* produce weekly graphs over a time interval longer than 1 week (i.e. for a month, produce 4 week-long graphs)
* produce daily aggregate average graph.  What if a line was drawn for each day but the more recent, the darker it is, would that look good?  easy to see changes?
* produce weekly aggregate average graph
* produce change graphs - weekly, daily, or monthly, Sun-Saturday with each time interval in a gradient color to see most trends over time
* calculate average glucose over data - use convolve and window?  https://stackoverflow.com/questions/15959819/time-series-averaging-in-numpy-python
* make time in TZ graph y-axes pinned to 0 and 100%
