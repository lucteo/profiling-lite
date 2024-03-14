import bisect
import lib.parse_dto as parse_dto
import lib.emit_dto as emit_dto


def emit_trace(parse_items):
    """Generates the emit DTO objects for the given parse items."""

    # Emit the two process tracks
    track_emitter = _TrackEmitter()
    yield from track_emitter.emit_process_tracks()

    stacks = _Stacks(track_emitter)
    threads = {}  # tid -> _ThreadData
    counter_tracks = {}  # tid -> track_uuid
    locations = {}  # locid -> (emit_dto.Location, name)
    open_zones = {}  # stack_ptr -> _StackData

    for item in parse_items:
        if isinstance(item, parse_dto.Stack):
            stacks.add_stack(end=item.end, begin=item.begin, name=item.name)
            yield from stacks.emit_pending_tracks()
        elif isinstance(item, parse_dto.Thread):
            uuid = track_emitter.next_uuid()
            yield track_emitter.thread_mapping_track(uuid, item.tid, item.thread_name)
            threads[item.tid] = _ThreadData(uuid)

        elif isinstance(item, parse_dto.Location):
            loc = emit_dto.Location(
                locid=item.locid,
                function_name=item.function_name,
                file_name=item.file_name,
                line_number=item.line_number,
            )
            locations[item.locid] = (loc, item.name)
            yield loc

        elif isinstance(item, parse_dto.ZoneStart):
            # If this zone announces a new thread, ensure we add the thread.
            if item.tid not in threads:
                uuid = track_emitter.next_uuid()
                yield track_emitter.thread_mapping_track(uuid, item.tid, "Unknown")
                threads[item.tid] = _ThreadData(uuid)

            # Check the stack and the thread of the zone
            thread = threads[item.tid]
            stack = thread.last_stack()
            if not stack or not stack.contains(item.stack_ptr):
                stack = stacks.stack_for_ptr(item.stack_ptr)
                yield from stacks.emit_pending_tracks()
            yield from thread.mark_stack(stack, item.timestamp)

            # Add the zone to the stack.
            loc_pair = locations[item.locid]
            yield from stack.start_zone(
                item.stack_ptr, item.timestamp, loc_pair[0], loc_pair[1]
            )
            open_zones[item.stack_ptr] = stack

        elif isinstance(item, parse_dto.ZoneEnd):
            stack = open_zones.pop(item.stack_ptr)
            yield from stack.end_zone(item.timestamp)
        elif isinstance(item, parse_dto.ZoneName):
            dto = open_zones[item.stack_ptr].open_zone_dto(item.stack_ptr)
            if dto:
                dto.name = item.name
        elif isinstance(item, parse_dto.ZoneFlow):
            dto = open_zones[item.stack_ptr].open_zone_dto(item.stack_ptr)
            if dto:
                dto.flows.append(item.flowid)
        elif isinstance(item, parse_dto.ZoneFlowTerminate):
            dto = open_zones[item.stack_ptr].open_zone_dto(item.stack_ptr)
            if dto:
                dto.flows_terminating.append(item.flowid)
        elif isinstance(item, parse_dto.ZoneCategory):
            dto = open_zones[item.stack_ptr].open_zone_dto(item.stack_ptr)
            if dto:
                dto.categories.append(item.category_name)
        elif isinstance(item, parse_dto.ZoneParam):
            dto = open_zones[item.stack_ptr].open_zone_dto(item.stack_ptr)
            if dto:
                dto.params[item.name] = item.value

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

    def __init__(self, track_emitter: _TrackEmitter):
        self._stacks = []
        self._track_emitter = track_emitter
        self._to_emit = []

    def add_stack(self, end, begin=0, name=None):
        """Adds an user-specified stack to the list of stacks."""
        stack = self._existing_stack_containing(end)
        if not stack:
            self._add_stack(end, begin, name)

    def stack_for_ptr(self, ptr):
        """Get the stack for the given pointer, creating a new one if necessary."""
        stack = self._existing_stack_containing(ptr)
        if stack:
            return stack

        # No stack found, create an implicit one
        return self._add_stack(ptr, name=f"Stack @{ptr}")

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

    def emit_pending_tracks(self):
        """Yields the pending tracks objects."""
        yield from self._to_emit
        self._to_emit = []

    def _add_stack(self, end, begin=0, name=None):
        """Adds a stack to the list of stacks."""
        uuid = self._track_emitter.next_uuid()
        stack = _StackData(uuid=uuid, end=end, begin=begin, name=name)
        bisect.insort_left(self._stacks, stack, key=lambda x: x.end)
        self._to_emit.append(self._track_emitter.stack_track(uuid, stack.name()))
        return stack


class _StackData:
    """Describes a stack, the zones added to it and its usage."""

    def __init__(self, uuid, end, begin=0, name=None):
        assert begin < end
        end = _round_up_to_page_size(end)
        self.end = end
        self.uuid = uuid
        self._lowest_seen = end
        self._begin = begin
        self._used = []  # (timestamp, used_bytes)
        if not name:
            name = f"Stack @{end}"
        self._name = name
        self._open_zone_ptr = None
        self._open_zone_dto = None

    def contains(self, ptr):
        """Check if the stack contains the given pointer."""
        lo = self._begin if self._begin > 0 else self._lowest_seen - 10 * 1024
        return ptr >= lo and ptr <= self.end

    def start_zone(self, ptr, timestamp, loc, loc_name):
        """Starts a zone in this stack."""
        if self._open_zone_dto:
            yield self._open_zone_dto

        assert self.contains(ptr)
        self._open_zone_ptr = ptr
        self._open_zone_dto = emit_dto.ZoneStart(
            track_uuid=self.uuid, timestamp=timestamp, loc=loc, name=loc_name
        )
        self._mark_usage(ptr, timestamp)

    def end_zone(self, timestamp):
        """Ends the current zone in this stack."""
        if self._open_zone_dto:
            yield self._open_zone_dto
            self._open_zone_dto = None
            self._open_zone_ptr = None
        yield emit_dto.ZoneEnd(track_uuid=self.uuid, timestamp=timestamp)

    def open_zone_dto(self, ptr):
        """Returns the DTO object for the open zone, if the open zone is for `ptr`."""
        if self._open_zone_ptr == ptr:
            return self._open_zone_dto
        return None

    def _mark_usage(self, stack_ptr, timestamp):
        """Mark the usage of `stack_ptr` inside this stack."""
        self._used = (timestamp, self.end - stack_ptr)
        if stack_ptr < self._lowest_seen:
            self._lowest_seen = stack_ptr

    def name(self):
        return self._name


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
