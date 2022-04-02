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
* read in multiple files, in parallel
** people will have potentially hundreds of files, many of them with overlap
* produce all-time graph
* produce last month graph
* produce daily aggregate average graph
* produce weekly aggregate average graph
