from dataclasses import dataclass, field


@dataclass
class Stack:
    """Describes a stack under which we can execute code."""

    begin: int
    end: int
    name: str


@dataclass
class Thread:
    """Describes a thread in a profiling trace."""

    tid: int
    thread_name: str


@dataclass
class Location:
    """Describes a location in the source code."""

    locid: int
    name: str
    function_name: str
    file_name: str
    line_number: int


@dataclass
class ZoneStart:
    """Describes the start of an execution zone."""

    stack_ptr: int
    tid: int
    timestamp: int
    locid: int


@dataclass
class ZoneEnd:
    """Describes the start of an execution zone."""

    stack_ptr: int
    timestamp: int


@dataclass
class ZoneName:
    """Describes a dynamic name given to an execution zone."""

    stack_ptr: int
    name: str


@dataclass
class ZoneFlow:
    """Describes a flow ID associated with an execution zone."""

    stack_ptr: int
    flowid: int


@dataclass
class ZoneFlowTerminate:
    """Describes a flow ID associated with an execution zone; the flow terminates after the zone."""

    stack_ptr: int
    flowid: int


@dataclass
class ZoneCategory:
    """Describes a category associated with execution zone."""

    stack_ptr: int
    category_name: str


@dataclass
class ZoneParam:
    """Describes a parameter for a zone."""

    stack_ptr: int
    name: str
    value: str | bool | int | float


@dataclass
class CounterTrack:
    """Describes a track for counter."""

    tid: int
    name: str


@dataclass
class CounterValue:
    """Describes a value for a counter."""

    tid: int
    timestamp: int
    value: int | float
