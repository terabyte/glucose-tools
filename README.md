# Glucose Monitoring Tools

This tool reads in data taken from the Freestyle Libre glucose monitor, aggregates it, then generates graphs and does analysis or whatever.

# How to Use

```
# only tested with python3+
$ pyenv virtualenv glucose
$ pyenv local glucose
$ pip install -r requirements.txt
$ ./analyze.py
```

# TODO
* clean up graph, make it prettier
* tag data points - green if surrounding 24hrs is >80% in target?
* produce weekly graphs over a time interval longer than 1 week (i.e. for a month, produce 4 week-long graphs)
* produce daily aggregate average graph
* produce weekly aggregate average graph
* produce change graphs - weekly, daily, or monthly, Sun-Saturday with each time interval in a gradient color to see most trends over time
* calculate average glucose over data - use convolve and window?  https://stackoverflow.com/questions/15959819/time-series-averaging-in-numpy-python
