from dataclasses import dataclass, field
import lib.parse_dto as parse_dto
import lib.dto as dto


def parse_to_trace(parse_items):
    """Converts the parse items to a trace."""

    threads = {}  # tid -> _ThreadData
    counter_tracks = {}
    locations = {}
    spawns = {}  # spawn_id -> _SpawnData
    thread_switch_data = _ThreadSwitchData()

    def _thread(tid):
        if tid not in threads:
            threads[tid] = _ThreadData(tid, "Unknown")
        return threads[tid]

    for item in parse_items:
        if isinstance(item, parse_dto.Thread):
            threads[item.tid] = _ThreadData(item.tid, item.thread_name)
        elif isinstance(item, parse_dto.CounterTrack):
            counter_tracks[item.tid] = dto.CounterTrack(item.name)

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
            _thread(item.tid).add_zone_start(item.timestamp, loc)
        elif isinstance(item, parse_dto.ZoneEnd):
            _thread(item.tid).add_zone_end(item.timestamp)
        elif isinstance(item, parse_dto.ZoneName):
            _thread(item.tid).current_zone().name = item.name
        elif isinstance(item, parse_dto.ZoneFlow):
            _thread(item.tid).current_zone().flows.append(item.flowid)
        elif isinstance(item, parse_dto.ZoneCategory):
            _thread(item.tid).current_zone().categories.append(item.category_name)
        elif isinstance(item, parse_dto.ZoneParam):
            _thread(item.tid).current_zone().params[item.name] = item.value

        elif isinstance(item, parse_dto.CounterValue):
            counter_value = dto.CounterValue(timestamp=item.timestamp, value=item.value)
            counter_tracks[item.tid].values.append(counter_value)

        elif isinstance(item, parse_dto.ThreadSwitchStart):
            thread_switch_data.start_thread_switch(item.id, item.tid)
        elif isinstance(item, parse_dto.ThreadSwitchEnd):
            thread_switch_data.finish_thread_switch(item.id, item.tid, item.timestamp)

        elif isinstance(item, parse_dto.Spawn):
            spawns[item.spawn_id] = _SpawnData(
                item.spawn_id, _thread(item.tid), item.timestamp, item.num_threads
            )
        elif isinstance(item, parse_dto.SpawnContinue):
            spawns[item.spawn_id].thread_joining(_thread(item.tid), item.timestamp)
        elif isinstance(item, parse_dto.SpawnEnding):
            spawns[item.spawn_id].thread_leaving(_thread(item.tid), item.timestamp)
        elif isinstance(item, parse_dto.SpawnDone):
            spawns[item.spawn_id].done(_thread(item.tid), item.timestamp)

        else:
            raise ValueError(f"Unknown object {item}")

    # Generate thread switch tracks
    extra_tracks = thread_switch_data.generate_thread_switch_tracks(threads)

    # Wrap everything in a Trace object
    trace = dto.Trace()
    trace.process_tracks.append(dto.ProcessTrack(pid=0, name="Process"))
    trace.process_tracks[0].subtracks = [t.zones_track for t in threads.values()]
    trace.process_tracks[0].subtracks.extend(extra_tracks)
    trace.process_tracks[0].counter_tracks.extend(counter_tracks.values())
    return trace


class _ThreadData:
    def __init__(self, tid, name):
        self.tid = tid
        self.name = name
        self.zones_track = dto.ZonesTrack(tid=tid, name=name)
        self.open_zones = []

    def add_zone_start(self, timestamp, loc):
        zone = dto.Zone(self.tid, timestamp, 0, loc, loc.name)
        self.open_zones.append(zone)
        self.zones_track.zones.append(zone)

    def add_zone_end(self, timestamp):
        if self.open_zones:
            self.current_zone().end = timestamp
            self.open_zones.pop()

    def add_open_zone(self, zone):
        self.open_zones.append(zone)
        self.zones_track.zones.append(zone)

    def add_closed_zone(self, zone):
        self.zones_track.zones.append(zone)

    def current_zone(self):
        assert len(self.open_zones) > 0, "No open zone; invalid capture file."
        return self.open_zones[-1]


class _ThreadSwitchData:
    def __init__(self):
        self._started = {}
        self._switches = []

    def start_thread_switch(self, id, tid):
        self._started[id] = tid

    def finish_thread_switch(self, id, tid, timestamp):
        start_tid = self._started.pop(id)
        if start_tid != tid:
            self._switches.append((start_tid, tid, timestamp))

    def generate_thread_switch_tracks(self, threads):
        if not self._switches:
            return []

        new_tid = 1
        r = []
        for t in threads.values():
            t2 = _ThreadData(new_tid, f"Thread switches: {t.name}")
            new_tid += 1

            min_timestamp = t.zones_track.zones[0].start
            max_timestamp = max([z.end for z in t.zones_track.zones])

            last_timestamp = min_timestamp
            last_tid = t.tid
            for timestamp, tid in self._switches_for_thread(t.tid):
                t2.add_closed_zone(
                    _create_thread_zone(
                        t2.tid, last_timestamp, timestamp, threads[last_tid].name
                    )
                )
                last_timestamp = timestamp
                last_tid = tid

            if last_timestamp < max_timestamp:
                t2.add_closed_zone(
                    _create_thread_zone(
                        t2.tid, last_timestamp, max_timestamp, threads[last_tid].name
                    )
                )

            r.append(t2.zones_track)
        return r

    def _switches_for_thread(self, tid):
        for s in self._switches:
            if s[0] == tid:
                yield (s[2], s[1])
            if s[1] == tid:
                yield (s[2], s[0])


class _SpawnData:
    def __init__(self, spawn_id, starting_thread, timestamp, num_threads):
        self.spawn_id = spawn_id
        self.previous_zones = []
        self.num_threads = num_threads

        starting_thread.add_closed_zone(
            _create_spawn_zone(starting_thread.tid, timestamp, "Spawn", spawn_id)
        )
        self.previous_zones = _split_open_zones(starting_thread, timestamp)

    def thread_joining(self, thread, timestamp):
        thread.add_closed_zone(
            _create_spawn_zone(thread.tid, timestamp, "Spawn continue", self.spawn_id)
        )

    def thread_leaving(self, thread, timestamp):
        thread.add_closed_zone(
            _create_spawn_zone(
                thread.tid, timestamp, "Spawn finishing", self.spawn_id + 1
            )
        )

    def done(self, thread, timestamp):
        # Continue the previous zones
        for zone in self.previous_zones:
            thread.add_open_zone(zone)
        thread.add_closed_zone(
            _create_spawn_zone(thread.tid, timestamp, "Spawn done", self.spawn_id + 1)
        )


def _split_open_zones(from_thread, timestamp):
    """Ends all the open zones in `from_thread` and return new corresponding zones starting with `timestamp`."""
    res = []
    for zone in from_thread.open_zones:
        zone2 = _clone_zone(zone, name_prefix="(spawn clone) ")
        zone.end = timestamp
        zone2.start = timestamp
        res.append(zone2)
    return res


def _clone_zone(zone, name_prefix=""):
    return dto.Zone(
        zone.tid,
        zone.start,
        zone.end,
        zone.loc,
        name_prefix + zone.name,
        zone.params.copy(),
        zone.flows.copy(),
        zone.categories.copy(),
    )


def _create_spawn_zone(tid, timestamp, name, flow_id):
    return dto.Zone(
        tid, timestamp, timestamp, None, name, flows=[flow_id], categories=["spawn"]
    )


def _create_thread_zone(tid, start, end, name):
    return dto.Zone(tid, start, end, None, name)
