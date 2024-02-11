from dataclasses import dataclass, field


@dataclass
class Thread:
    """Describes a thread in a profiling trace."""

    tid: int
    thread_name: str


@dataclass
class CounterTrack:
    """Describes a track for counter."""

    tid: int
    name: str


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

    tid: int
    timestamp: int
    locid: int


@dataclass
class ZoneEnd:
    """Describes the start of an execution zone."""

    tid: int
    timestamp: int


@dataclass
class ZoneName:
    """Describes a dynamic name given to an execution zone."""

    tid: int
    name: str


@dataclass
class ZoneFlow:
    """Describes a flow ID associated with an execution zone."""

    tid: int
    flowid: int


@dataclass
class ZoneCategory:
    """Describes a category associated with execution zone."""

    tid: int
    category_name: str


@dataclass
class ZoneParam:
    """Describes a parameter for a zone."""

    tid: int
    name: str
    value: str | bool | int | float


@dataclass
class CounterValue:
    """Describes a value for a counter."""

    tid: int
    timestamp: int
    value: int | float


@dataclass
class ThreadSwitchStart:
    """Describes the start of a potential thread switch."""

    tid: int
    id: int


@dataclass
class ThreadSwitchEnd:
    """Describes the end of a potential thread switch."""

    tid: int
    timestamp: int
    id: int


@dataclass
class Spawn:
    spawn_id: int
    tid: int
    timestamp: int
    num_threads: int


@dataclass
class SpawnContinue:
    spawn_id: int
    tid: int
    timestamp: int


@dataclass
class SpawnEnding:
    spawn_id: int
    tid: int
    timestamp: int


@dataclass
class SpawnDone:
    spawn_id: int
    tid: int
    timestamp: int
