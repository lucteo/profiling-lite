from dataclasses import dataclass, field


@dataclass
class Location:
    """Describes a location in the source code."""

    locid: int
    name: str
    function_name: str
    file_name: str
    line_number: int


@dataclass
class Zone:
    """Describes an execution zone."""

    start: int
    end: int
    loc: Location
    name: str
    params: dict = field(default_factory=dict)
    flows: list[int] = field(default_factory=list)
    flows_terminating: list[int] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


@dataclass
class ZonesTrack:
    """Describes a track for zones."""

    tid: int
    name: str
    zones: list[Zone] = field(default_factory=list)


@dataclass
class CounterValue:
    """Describes a value in time for a counter track."""

    timestamp: int
    value: int | float


@dataclass
class CounterTrack:
    """Describes a track for counter."""

    name: str
    values: list[CounterValue] = field(default_factory=list)


@dataclass
class ProcessTrack:
    """Describes a track for a process."""

    pid: int
    name: str
    subtracks: list[ZonesTrack] = field(default_factory=list)
    counter_tracks: list[CounterTrack] = field(default_factory=list)


@dataclass
class Trace:
    """Describes a trace with multiple tracks."""

    process_tracks: list[ProcessTrack] = field(default_factory=list)
