import bisect
import lib.parse_dto as parse_dto
import lib.emit_dto as emit_dto
from dataclasses import dataclass, field


def emit_trace(parse_items):
    """Generates the emit DTO objects for the given parse items."""

    # Emit the two process tracks
    track_emitter = _TrackEmitter()
    yield from track_emitter.emit_process_tracks()

    stacks = _Stacks()
    threads = {}  # tid -> _ThreadData
    counter_tracks = {}  # tid -> track_uuid
    locations = {}
    open_zones = {}  # stack_ptr -> _ZoneData

    for item in parse_items:
        if isinstance(item, parse_dto.Stack):
            stacks.add_stack(end=item.end, begin=item.begin, name=item.name)
        elif isinstance(item, parse_dto.Thread):
            uuid = track_emitter.next_uuid()
            yield track_emitter.thread_mapping_track(uuid, item.tid, item.thread_name)
            threads[item.tid] = _ThreadData(uuid)

        elif isinstance(item, parse_dto.Location):
            locations[item.locid] = _Location(
                item.locid,
                item.name,
                item.file_name,
                item.function_name,
                item.line_number,
            )

        elif isinstance(item, parse_dto.ZoneStart):
            # If this zone announces a new thread, ensure we add the thread.
            if item.tid not in threads:
                uuid = track_emitter.next_uuid()
                yield track_emitter.thread_mapping_track(uuid, item.tid, "Unknown")
                threads[item.tid] = _ThreadData(uuid)

            loc = locations[item.locid]
            zone = _Zone(start=item.timestamp, end=0, loc=loc, name=loc.name)
            open_zones[item.stack_ptr] = zone

            # Check the stack and the thread of the zone
            thread = threads[item.tid]
            stack = thread.last_stack()
            if not stack or not stack.contains(item.stack_ptr):
                stack = stacks.stack_for_ptr(item.stack_ptr)
            yield from thread.mark_stack(stack, item.timestamp)

            # Add the zone to the stack.
            stack.add_zone(zone)

        elif isinstance(item, parse_dto.ZoneEnd):
            zone = open_zones.pop(item.stack_ptr)
            zone.end = item.timestamp
        elif isinstance(item, parse_dto.ZoneName):
            open_zones[item.stack_ptr].name = item.name
        elif isinstance(item, parse_dto.ZoneFlow):
            open_zones[item.stack_ptr].flows.append(item.flowid)
        elif isinstance(item, parse_dto.ZoneFlowTerminate):
            open_zones[item.stack_ptr].flows_terminating.append(item.flowid)
        elif isinstance(item, parse_dto.ZoneCategory):
            open_zones[item.stack_ptr].categories.append(item.category_name)
        elif isinstance(item, parse_dto.ZoneParam):
            open_zones[item.stack_ptr].params[item.name] = item.value

        elif isinstance(item, parse_dto.CounterTrack):
            uuid = track_emitter.next_uuid()
            yield track_emitter.counter_track(uuid, item.name)
            counter_tracks[item.tid] = uuid
        elif isinstance(item, parse_dto.CounterValue):
            yield emit_dto.CounterValue(
                track_uuid=counter_tracks[item.tid],
                timestamp=item.timestamp,
                value=item.value,
            )

        else:
            raise ValueError(f"Unknown object {item}")

    # Stacks and zones tracks
    for zones_track in stacks.zone_tracks():
        uuid = track_emitter.next_uuid()
        yield track_emitter.stack_track(uuid, zones_track.name)
        yield from _emit_zones(zones_track.zones, uuid)

    # Close the thread mapping tracks
    for t in threads.values():
        yield from t.close()


class _TrackEmitter:
    def __init__(self):
        self._track_uuid_gen = _track_id_gen()
        self.stacks_track_uuid = next(self._track_uuid_gen)
        self.thread_mapping_track_uuid = next(self._track_uuid_gen)

    def emit_process_tracks(self):
        """Emits the process tracks for the entire capture."""
        yield emit_dto.ProcessTrack(
            track_uuid=self.stacks_track_uuid, pid=0, name="Stacks and zones"
        )
        yield emit_dto.ProcessTrack(
            track_uuid=self.thread_mapping_track_uuid, pid=1, name="Threads mapping"
        )

    def next_uuid(self):
        """Generates the next track uuid."""
        return next(self._track_uuid_gen)

    def stack_track(self, uuid, name):
        """Emits a track for representing zones over stacks."""
        return emit_dto.Thread(
            track_uuid=uuid,
            tid=uuid,
            pid=0,
            thread_name=name,
        )

    def thread_mapping_track(self, uuid, tid, name):
        """Emits a thread-mapping track."""
        return emit_dto.Thread(
            track_uuid=uuid,
            tid=tid,
            pid=1,
            thread_name=name,
        )

    def counter_track(self, uuid, name):
        """Emits a counter track."""
        return emit_dto.CounterTrack(
            track_uuid=uuid,
            parent_track=self.thread_mapping_track_uuid,
            name=name,
        )


class _Stacks:
    """Keeps track of the stacks we are using in this trace."""

    def __init__(self):
        self._stacks = []

    def add_stack(self, end, begin=0, name=None):
        """Adds an user-specified stack to the list of stacks."""
        # First, check if don't already have the stack
        stack = self._existing_stack_containing(end)
        if stack:
            # Stack found; try updating information.
            stack.update(begin, name)
        else:
            # No stack found, create one
            stack = _StackData(end, begin, name)
            bisect.insort_left(self._stacks, stack, key=lambda x: x.end)

    def stack_for_ptr(self, ptr):
        """Get the stack for the given pointer, creating a new one if necessary."""
        stack = self._existing_stack_containing(ptr)
        if stack:
            return stack

        # No stack found, create an implicit one
        stack = _StackData(end=ptr)
        self.add_stack(stack)
        return stack

    def _existing_stack_containing(self, ptr):
        """Check if we have an existing stack that contains `ptr`, and, if so, return it."""
        idx = bisect.bisect_left(self._stacks, ptr, key=lambda x: x.end)
        if idx >= len(self._stacks):
            return None
        stack = self._stacks[idx]
        if stack.contains(ptr):
            return stack
        else:
            return None

    def zone_tracks(self):
        """Yields the zones tracks for all the stacks."""
        return [s.zones_track for s in self._stacks]


class _StackData:
    """Describes a stack, the zones added to it and its usage."""

    def __init__(self, end, begin=0, name=None):
        assert begin < end
        end = _round_up_to_page_size(end)
        self.end = end
        self._lowest_seen = end
        self._begin = begin
        self._used = []  # (timestamp, used_bytes)
        if not name:
            name = f"Stack @{end}"
        self.zones_track = _ZonesTrack(tid=end, name=name)

    def contains(self, ptr):
        """Check if the stack contains the given pointer."""
        lo = self._begin if self._begin > 0 else self._lowest_seen - 10 * 1024
        return ptr >= lo and ptr <= self.end

    def add_zone(self, zone):
        """Adds a zone to the stack."""
        self.zones_track.zones.append(zone)
        self._mark_usage(zone.start, zone.end)

    def update(self, begin, name):
        """Update an existing stack with new information."""
        if begin > 0:
            self._begin = begin
        if name and not self.zones_track.name:
            self.zones_track.name = name

    def _mark_usage(self, stack_ptr, timestamp):
        """Mark the usage of `stack_ptr` inside this stack."""
        self._used = (timestamp, self.end - stack_ptr)
        if stack_ptr < self._lowest_seen:
            self._lowest_seen = stack_ptr

    def name(self):
        return self.zones_track.name


def _round_up_to_page_size(x):
    return (x + 4095) & ~4095


class _ThreadData:
    """Describes a thread, how it executes code that correspond to various stacks."""

    def __init__(self, uuid):
        self.uuid = uuid
        self._current_stack = None
        self._last_switch_timestamp = None
        self._last_timestamp = None

    def last_stack(self):
        """Returns the last stack used by the thread."""
        return self._current_stack

    def mark_stack(self, stack, timestamp):
        """Marks the usage of a stack by the thread."""
        if not self._last_switch_timestamp:
            self._last_switch_timestamp = timestamp
            self._last_timestamp = timestamp
            self._current_stack = stack
            yield self._emit_zone_start(stack, timestamp)
        elif self._current_stack != stack:
            yield self._emit_zone_end(timestamp)
            yield self._emit_zone_start(stack, timestamp)
            self._last_switch_timestamp = timestamp
            self._last_timestamp = timestamp
            self._current_stack = stack
        else:
            self._last_timestamp = timestamp

    def close(self):
        if self._last_timestamp:
            yield self._emit_zone_end(self._last_timestamp)

    def _emit_zone_start(self, stack, timestamp):
        return emit_dto.ZoneStart(
            track_uuid=self.uuid,
            timestamp=timestamp,
            loc=None,
            name=stack.name(),
        )

    def _emit_zone_end(self, timestamp):
        return emit_dto.ZoneEnd(track_uuid=self.uuid, timestamp=timestamp)


def _track_id_gen():
    """Generates unique track ids."""
    track_uuid = 0
    while True:
        yield track_uuid
        track_uuid += 1


def _emit_zones(zones, track_uuid):
    zones_to_end = []
    for zone in zones:
        # Emit all zone ends that are before the start of this zone.
        while zones_to_end and zones_to_end[0] <= zone.start:
            yield emit_dto.ZoneEnd(track_uuid=track_uuid, timestamp=zones_to_end[0])
            del zones_to_end[0]

        # Is this an instant zone?
        if zone.start == zone.end:
            zone_instant = emit_dto.ZoneInstant(
                track_uuid=track_uuid,
                timestamp=zone.start,
                loc=_cvt_location(zone.loc),
                name=zone.name,
                params=zone.params,
                flows=zone.flows,
                flows_terminating=zone.flows_terminating,
                categories=zone.categories,
            )
            yield zone_instant
            continue

        # Emit this zone start.
        zone_start = emit_dto.ZoneStart(
            track_uuid=track_uuid,
            timestamp=zone.start,
            loc=_cvt_location(zone.loc),
            name=zone.name,
            params=zone.params,
            flows=zone.flows,
            flows_terminating=zone.flows_terminating,
            categories=zone.categories,
        )
        yield zone_start

        if zone.end == zone.start:
            # Also emit the zone end.
            yield emit_dto.ZoneEnd(track_uuid=track_uuid, timestamp=zone.end)
        else:
            # Keep track of the zone end.
            zones_to_end.insert(0, zone.end)

    # Emit remaining zone ends.
    for end in zones_to_end:
        yield emit_dto.ZoneEnd(track_uuid=track_uuid, timestamp=end)


def _cvt_location(obj):
    if obj is None:
        return None
    return emit_dto.Location(
        locid=obj.locid,
        function_name=obj.function_name,
        file_name=obj.file_name,
        line_number=obj.line_number,
    )


@dataclass
class _Location:
    """Describes a location in the source code."""

    locid: int
    name: str
    function_name: str
    file_name: str
    line_number: int


@dataclass
class _Zone:
    """Describes an execution zone."""

    start: int
    end: int
    loc: _Location
    name: str
    params: dict = field(default_factory=dict)
    flows: list[int] = field(default_factory=list)
    flows_terminating: list[int] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


@dataclass
class _ZonesTrack:
    """Describes a track for zones."""

    tid: int
    name: str
    zones: list[_Zone] = field(default_factory=list)
