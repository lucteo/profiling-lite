import bisect
import lib.parse_dto as parse_dto
import lib.dto as dto


def parse_to_trace(parse_items):
    """Converts the parse items to a trace."""

    stacks = _Stacks()
    threads = {}  # tid -> _ThreadData
    counter_tracks = {}
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
            stacks.add_stack(_StackData(item.begin, item.end, item.name))
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
            counter_tracks[item.tid] = dto.CounterTrack(item.name)
        elif isinstance(item, parse_dto.CounterValue):
            counter_value = dto.CounterValue(timestamp=item.timestamp, value=item.value)
            counter_tracks[item.tid].values.append(counter_value)

        else:
            raise ValueError(f"Unknown object {item}")

    tracks = stacks.zone_tracks()
    tracks.extend([t.zones_track() for t in threads.values()])

    # Wrap everything in a Trace object
    trace = dto.Trace()
    trace.process_tracks.append(dto.ProcessTrack(pid=0, name="Process"))
    trace.process_tracks[0].subtracks = tracks
    trace.process_tracks[0].counter_tracks.extend(counter_tracks.values())
    return trace


class _Stacks:
    """Keeps track of the stacks we are using in this trace."""

    def __init__(self):
        self._stacks = []

    def add_stack(self, stack):
        """Adds an user-specified stack to the list of stacks."""
        bisect.insort_left(self._stacks, stack, key=lambda x: x.end)

    def stack_for_ptr(self, ptr):
        """Get the stack for the given pointer, creating a new one if necessary."""
        stack = self._existing_stack_containing(ptr)
        if stack:
            return stack

        # No stack found, create an implicit one
        stack = _StackData(begin=0, end=ptr)
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

    def __init__(self, begin, end, name=None):
        assert begin < end
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

    def _mark_usage(self, stack_ptr, timestamp):
        """Mark the usage of `stack_ptr` inside this stack."""
        self._used = (timestamp, self.end - stack_ptr)
        if stack_ptr < self._lowest_seen:
            self._lowest_seen = stack_ptr

    def name(self):
        return self.zones_track.name


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
            r.zones.append(
                dto.Zone(
                    start=last_timestamp,
                    end=timestamp,
                    loc=None,
                    name=last_stack.name(),
                )
            )
            last_timestamp = timestamp
            last_stack = stack
        return r
