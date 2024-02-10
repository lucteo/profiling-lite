import lib.dto as dto
import lib.emit_dto as emit_dto


def emit_trace(trace, writer):
    """Emits the trace items to the writer in the appropriate order."""
    uuid_gen = _track_uuid_gen()
    for process_track in trace.process_tracks:
        process_uuid = next(uuid_gen)
        _emit_process_track(writer, process_track, process_uuid)

        for zones_track in process_track.subtracks:
            thread_uuid = next(uuid_gen)
            _emit_thread_track(writer, zones_track, thread_uuid, process_track.pid)
            _emit_thread_zones(writer, zones_track.zones, thread_uuid)

        for counter_track in process_track.counter_tracks:
            counter_uuid = next(uuid_gen)
            _emit_counter_track(writer, counter_track, counter_uuid, process_uuid)
            _emit_counter_values(writer, counter_track.values, counter_uuid)


def _track_uuid_gen():
    track_uuid = 0
    while True:
        yield track_uuid
        track_uuid += 1


def _emit_process_track(writer, process_track, track_uuid):
    process = emit_dto.ProcessTrack(
        track_uuid=track_uuid, pid=process_track.pid, name=process_track.name
    )
    writer.add(process)


def _emit_thread_track(writer, zones_track, track_uuid, pid):
    thread = emit_dto.Thread(
        track_uuid=track_uuid,
        pid=pid,
        tid=zones_track.tid,
        thread_name=zones_track.name,
    )
    writer.add(thread)


def _emit_thread_zones(writer, zones, track_uuid):
    for zone in zones:
        zone_start = emit_dto.ZoneStart(
            track_uuid=track_uuid,
            timestamp=zone.start,
            loc=_cvt_location(zone.loc),
            name=zone.name,
            params=zone.params,
            flows=zone.flows,
            categories=zone.categories,
        )
        writer.add(zone_start)

        zone_end = emit_dto.ZoneEnd(
            track_uuid=track_uuid, timestamp=zone.end, flows=zone.flows
        )
        writer.add(zone_end)


def _emit_counter_track(writer, counter_track, track_uuid, process_uuid):
    counter = emit_dto.CounterTrack(
        track_uuid=track_uuid, parent_track=process_uuid, name=counter_track.name
    )
    writer.add(counter)


def _emit_counter_values(writer, values, track_uuid):
    for value in values:
        counter_value = emit_dto.CounterValue(
            track_uuid=track_uuid, timestamp=value.timestamp, value=value.value
        )
        writer.add(counter_value)


def _cvt_location(obj):
    return emit_dto.Location(
        locid=obj.locid,
        function_name=obj.function_name,
        file_name=obj.file_name,
        line_number=obj.line_number,
    )
