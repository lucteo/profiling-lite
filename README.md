# profiling-lite
A small framework for profiling applications.

It defines a small set of profiling primitives that can be used to create [Perfetto](https://perfetto.dev/) traces.


## Text format

The text format is based on .csv. Every line is of the form:
```text
COMMAND, args...
```

Lines starting with `#` are considered comments.

Supported commands:
* `THREAD, tid, string`
  * Defines a thread and gives it a name.
  * The `tid` argument must be unique among threads.
* `COUNTERTRACK, tid, name`
  * Defines a counter track and gives it a name.
  * The `tid` argument must be unique among counter tracks.
* `LOCATION, locid, name, function, file, line`
  * Defines a location in the code.
* `ZONE_START, tid, timestamp, locid`
  * Specifies the start a zone stack; uses the name from the location.
* `ZONE_END, tid, timestamp`
  * Specifies the end of the last started zone on the thread.
* `ZONE_NAME, tid, text`
  * Overrides the name of the last started zone.
* `ZONE_PARAM, tid, name, value`
  * Adds a parameter to the current zone.
* `ZONE_FLOW, tid, flowid`
  * Defines a flow for the current zone.
* `ZONE_CATEGORY, tid, category_name`
  * Adds a category for the current zone.
* `COUNTERVALUE, tid, timestamp, value`
  * Adds a value / timestamp pair for a counter track.
