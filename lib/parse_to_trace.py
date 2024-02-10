import lib.parse_dto as parse_dto
import lib.dto as dto


def parse_to_trace(parse_items):
    """Converts the parse items to a trace."""

    threads = {}
    counter_tracks = {}
    locations = {}
    open_zones_per_thread = {}  # tid -> list of zones
    for item in parse_items:
        if isinstance(item, parse_dto.Thread):
            threads[item.tid] = dto.ZonesTrack(tid=item.tid, name=item.thread_name)
            open_zones_per_thread[item.tid] = []
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
            zone = dto.Zone(
                tid=item.tid, start=item.timestamp, end=0, loc=loc, name=loc.name
            )
            open_zones_per_thread[item.tid].append(zone)
            threads[item.tid].zones.append(zone)
        elif isinstance(item, parse_dto.ZoneEnd):
            open_zones_per_thread[item.tid][-1].end = item.timestamp
            open_zones_per_thread[item.tid].pop()
        elif isinstance(item, parse_dto.ZoneName):
            open_zones_per_thread[item.tid][-1].name = item.name
        elif isinstance(item, parse_dto.ZoneFlow):
            open_zones_per_thread[item.tid][-1].flows.append(item.flowid)
        elif isinstance(item, parse_dto.ZoneCategory):
            open_zones_per_thread[item.tid][-1].categories.append(item.category_name)
        elif isinstance(item, parse_dto.ZoneParam):
            open_zones_per_thread[item.tid][-1].params[item.name] = item.value

        elif isinstance(item, parse_dto.CounterValue):
            counter_value = dto.CounterValue(timestamp=item.timestamp, value=item.value)
            counter_tracks[item.tid].values.append(counter_value)

        else:
            raise ValueError(f"Unknown object {item}")

    # Wrap everything in a Trace object
    trace = dto.Trace()
    trace.process_tracks.append(dto.ProcessTrack(pid=0, name="Process"))
    trace.process_tracks[0].subtracks.extend(threads.values())
    trace.process_tracks[0].counter_tracks.extend(counter_tracks.values())
    return trace
