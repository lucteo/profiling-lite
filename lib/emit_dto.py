from dataclasses import dataclass, field


@dataclass
class ProcessTrack:
    """Describes a process track in a profiling trace."""

    track_uuid: int
    pid: int
    name: str


@dataclass
class Thread:
    """Describes a thread in a profiling trace."""

    track_uuid: int
    pid: int
    tid: int
    thread_name: str


@dataclass
class CounterTrack:
    """Describes a track for counter."""

    track_uuid: int
    parent_track: int
    name: str


@dataclass
class Location:
    """Describes a location in the source code."""

    locid: int
    function_name: str
    file_name: str
    line_number: int


@dataclass
class Zone:
    """Describes an execution zone."""

    track_uuid: int
    start: int
    end: int
    loc: Location
    name: str
    params: dict = field(default_factory=dict)
    flows: list[int] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


@dataclass
class ZoneStart:
    """Describes the start of an execution zone."""

    track_uuid: int
    timestamp: int
    loc: Location
    name: str
    params: dict = field(default_factory=dict)
    flows: list[int] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


@dataclass
class ZoneEnd:
    """Describes the start of an execution zone."""

    track_uuid: int
    timestamp: int
    flows: list[int] = field(default_factory=list)


@dataclass
class ZoneParam:
    """Describes a parameter for a zone."""

    name: str
    value: str


@dataclass
class CounterValue:
    """Describes a value for a counter."""

    track_uuid: int
    timestamp: int
    value: int | float
