from dataclasses import dataclass, field


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
class Zone:
    """Describes an execution zone."""

    tid: int
    start: int
    end: int
    loc: Location
    name: str
    params: dict = field(default_factory=dict)
    flows: list[int] = field(default_factory=list)


@dataclass
class ZoneStart:
    """Describes the start of an execution zone."""

    tid: int
    timestamp: int
    loc: Location
    name: str
    params: dict = field(default_factory=dict)
    flows: list[int] = field(default_factory=list)


@dataclass
class ZoneEnd:
    """Describes the start of an execution zone."""

    tid: int
    timestamp: int
    name: str
    flows: list[int] = field(default_factory=list)


@dataclass
class ZoneInstant:
    """Describes a zero-duration zone."""

    tid: int
    timestamp: int
    name: str
    flows: list[int] = field(default_factory=list)


@dataclass
class ZoneParam:
    """Describes a parameter for a zone."""

    tid: int
    name: str
    value: str | bool | int | float
