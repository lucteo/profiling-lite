import perfetto_trace_pb2 as pb2
import lib.dto as dto


class PerfettoWriter:
    """Knows how to write a perfetto trace file."""

    def __init__(self):
        self._trace = pb2.Trace()

    def write(self, filename):
        """Writes the trace to a file."""
        with open(filename, "wb") as f:
            f.write(self._trace.SerializeToString())

    def add_thread(self, t: dto.Thread):
        """Adds a thread track to the trace."""
        packet = self._trace.packet.add()
        packet.track_descriptor.uuid = t.tid
        packet.track_descriptor.thread.pid = 0
        packet.track_descriptor.thread.tid = t.tid
        packet.track_descriptor.thread.thread_name = t.thread_name

    def add_location(self, l: dto.Location):
        """Adds a location to the trace."""
        packet = self._trace.packet.add()
        location = packet.interned_data.source_locations.add()
        location.iid = l.locid
        location.file_name = l.file_name
        location.function_name = l.function_name
        location.line_number = l.line_number


    def add_zone_start(self, z: dto.ZoneStart):
        """Adds a zone start event to the trace."""
        packet = self._trace.packet.add()
        packet.timestamp = z.timestamp
        packet.track_event.type = pb2.TrackEvent.Type.TYPE_SLICE_BEGIN
        packet.track_event.track_uuid = z.tid
        packet.track_event.name = z.name
        for id in z.flows:
            packet.track_event.flow_ids.append(id)
        if z.loc:
            packet.track_event.source_location.iid = z.loc.locid
            packet.track_event.source_location.file_name = z.loc.file_name
            packet.track_event.source_location.function_name = z.loc.function_name
            packet.track_event.source_location.line_number = z.loc.line_number
        if z.params:
            annotation = packet.track_event.debug_annotations.add()
            annotation.name = "Parameters"
            for k, v in z.params.items():
                entry = annotation.dict_entries.add()
                entry.name = k
                entry.string_value = v
        packet.trusted_packet_sequence_id = 0

    def add_zone_end(self, z: dto.ZoneEnd):
        """Adds a zone end event to the trace."""
        packet = self._trace.packet.add()
        packet.timestamp = z.timestamp
        packet.track_event.type = pb2.TrackEvent.Type.TYPE_SLICE_END
        packet.track_event.track_uuid = z.tid
        for id in z.flows:
            packet.track_event.flow_ids.append(id)
        packet.trusted_packet_sequence_id = 0
