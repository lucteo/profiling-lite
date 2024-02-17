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
* `STACK, begin, end, name`
  * Defines a stack that may contain zones.
  * The range [`begin`, `end`] must not be overlapping between stacks.
  * If a stack region is not known by the program, the profiler tries its best of guessing the region.
* `THREAD, tid, string`
  * Defines a thread and gives it a name.
  * The `tid` argument must be unique among threads.
* `LOCATION, locid, name, function, file, line`
  * Defines a location in the code.
* `ZONE_START, stack_ptr, tid, timestamp, locid`
  * Specifies the start a zone stack; uses the name from the location.
  * `stack_ptr` is the pointer of the zone object on the stack; used for identifying the zone.
  * `stack_ptr` must be contained in a defined stack; if, not an implicit stack will be created.
* `ZONE_END, stack_ptr, timestamp`
  * Specifies the end of the last started zone on the thread.
* `ZONE_NAME, stack_ptr, text`
  * Overrides the name of the last started zone.
* `ZONE_PARAM, stack_ptr, name, value`
  * Adds a parameter to the current zone.
* `ZONE_FLOW, stack_ptr, flowid`
  * Defines a flow for the current zone.
* `ZONE_FLOW_T, stack_ptr, flowid`
  * Defines a flow for the current zone; the flow is terminated after this zone.
* `ZONE_CATEGORY, stack_ptr, category_name`
  * Adds a category for the current zone.
* `COUNTER_TRACK, tid, name`
  * Defines a counter track and gives it a name.
  * The `tid` argument must be unique among counter tracks.
* `COUNTER_VALUE, tid, timestamp, value`
  * Adds a value / timestamp pair for a counter track.

## How does it work?

* The profile tracks several things:
  * Stacks
    * These define the bounds in which the code can be executed.
    * Looking at the evolution of stacks is the main way to track the execution.
    * We also track an approximate filling of the stacks.
  * Threads
    * These will indicate which stacks are actively used at a given time.
  * Zones -- how various execution blocks happen inside a stack
    * The profiler displays the stacks as representing execution spaces.
    * Tracking execution happens in terms of stacks, not in terms of threads.
  * Counters
    * Independent tracks that allow the user to display graphs.

Notes:
* the profiler associates zones per stacks, not per threads
* we may have more stacks than threads in an application
* thread switches corresponds to threads switching the stacks they operate on
