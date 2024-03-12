import bisect
from dataclasses import dataclass
import lib.parse_dto as parse_dto
import lib.dto as dto
import lib.emit_dto as emit_dto


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

    def _thread(tid):
        if tid not in threads:
            threads[tid] = _ThreadData(tid, "Unknown")
        return threads[tid]

    def _get_stack_and_correlate_with_thread(tid, stack_ptr, timestamp):
        stack = _thread(tid).last_stack()
        if not stack or not stack.contains(stack_ptr):
            stack = stacks.stack_for_ptr(stack_ptr)
        _thread(tid).mark_stack(stack, timestamp)
        return stack

    for item in parse_items:
        if isinstance(item, parse_dto.Stack):
            stacks.add_stack(end=item.end, begin=item.begin, name=item.name)
        elif isinstance(item, parse_dto.Thread):
            threads[item.tid] = _ThreadData(item.tid, item.thread_name)

        elif isinstance(item, parse_dto.Location):
            locations[item.locid] = dto.Location(
                item.locid,
                item.name,
                item.file_name,
                item.function_name,
                item.line_number,
            )

        elif isinstance(item, parse_dto.ZoneStart):
            loc = locations[item.locid]
            zone = dto.Zone(start=item.timestamp, end=0, loc=loc, name=loc.name)
            open_zones[item.stack_ptr] = zone

            # Check the stack and the thread of the zone
            stack = _get_stack_and_correlate_with_thread(
                item.tid, item.stack_ptr, item.timestamp
            )
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

    # Thread mapping tracks
    for zones_track in [t.zones_track() for t in threads.values()]:
        uuid = track_emitter.next_uuid()
        yield track_emitter.thread_mapping_track(
            uuid, zones_track.tid, zones_track.name
        )
        yield from _emit_zones(zones_track.zones, uuid)


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
        self.zones_track = dto.ZonesTrack(tid=end, name=name)

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

    def __init__(self, tid, name):
        self.tid = tid
        self.name = name
        self.stacks_usage = []  # (timestamp, stack)

    def last_stack(self):
        """Returns the last stack used by the thread."""
        return self.stacks_usage[-1][1] if self.stacks_usage else None

    def mark_stack(self, stack, timestamp):
        """Marks the usage of a stack by the thread."""
        self.stacks_usage.append((timestamp, stack))

    def zones_track(self):
        """Yields a zones track corresponding to which stacks are actively used by the thread"""
        if not self.stacks_usage:
            return None

        r = dto.ZonesTrack(tid=self.tid, name=self.name)
        last_timestamp = self.stacks_usage[0][0]
        last_stack = self.stacks_usage[0][1]
        for timestamp, stack in self.stacks_usage:
            if stack == last_stack:
                continue
            r.zones.append(_thread_zone(last_timestamp, timestamp, last_stack.name()))
            last_timestamp = timestamp
            last_stack = stack
        timestamp_end = self.stacks_usage[-1][0]
        if timestamp_end != last_timestamp:
            r.zones.append(
                _thread_zone(last_timestamp, timestamp_end, last_stack.name())
            )
        return r


def _thread_zone(start, end, name):
    return dto.Zone(
        start=start,
        end=end,
        loc=None,
        name=name,
    )


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
