import perfetto_trace_pb2 as pb2
import lib.dto as dto


class PerfettoWriter:
    """Knows how to write a perfetto trace file."""

    def __init__(self):
        self._trace = pb2.Trace()
        self._last_track_id = 0
        self._thread_to_track = {}
        self._countertrack_to_track = {}

    def write(self, filename):
        """Writes the trace to a file."""
        with open(filename, "wb") as f:
            f.write(self._trace.SerializeToString())

    def add_thread(self, t: dto.Thread):
        """Adds a thread track to the trace."""
        self._last_track_id += 1
        self._thread_to_track[t.tid] = self._last_track_id
        packet = self._trace.packet.add()
        packet.track_descriptor.uuid = self._thread_to_track[t.tid]
        packet.track_descriptor.thread.pid = 0
        packet.track_descriptor.thread.tid = t.tid
        packet.track_descriptor.thread.thread_name = t.thread_name

    def add_counter_track(self, t: dto.CounterTrack):
        """Adds a thread track to the trace."""
        self._last_track_id += 1
        self._countertrack_to_track[t.tid] = self._last_track_id
        packet = self._trace.packet.add()
        packet.track_descriptor.uuid = self._last_track_id
        packet.track_descriptor.name = t.name
        packet.track_descriptor.counter.unit_name = "value"
        # packet.track_descriptor.counter = pb2.CounterDescriptor()

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
        packet.timestamp = z.ref.start
        packet.trusted_packet_sequence_id = 0
        packet.track_event.type = pb2.TrackEvent.Type.TYPE_SLICE_BEGIN
        packet.track_event.track_uuid = self._thread_to_track[z.ref.tid]
        packet.track_event.name = z.ref.name
        if z.ref.loc:
            packet.track_event.source_location.iid = z.ref.loc.locid
            packet.track_event.source_location.file_name = z.ref.loc.file_name
            packet.track_event.source_location.function_name = z.ref.loc.function_name
            packet.track_event.source_location.line_number = z.ref.loc.line_number
        if z.ref.params:
            annotation = packet.track_event.debug_annotations.add()
            annotation.name = "Parameters"
            for k, v in z.ref.params.items():
                entry = annotation.dict_entries.add()
                entry.name = k
                entry.string_value = v
        for id in z.ref.flows:
            packet.track_event.flow_ids.append(id)
        for category in z.ref.categories:
            packet.track_event.categories.append(category)

    def add_zone_end(self, z: dto.ZoneEnd):
        """Adds a zone end event to the trace."""
        packet = self._trace.packet.add()
        packet.timestamp = z.ref.end
        packet.trusted_packet_sequence_id = 0
        packet.track_event.type = pb2.TrackEvent.Type.TYPE_SLICE_END
        packet.track_event.track_uuid = self._thread_to_track[z.ref.tid]
        for id in z.ref.flows:
            packet.track_event.flow_ids.append(id)

    def add_counter_value(self, v: dto.CounterValue):
        """Adds a counter value to the trace."""
        packet = self._trace.packet.add()
        packet.timestamp = v.timestamp
        packet.trusted_packet_sequence_id = 0
        packet.track_event.type = pb2.TrackEvent.Type.TYPE_COUNTER
        packet.track_event.track_uuid = self._countertrack_to_track[v.tid]
        packet.track_event.counter_value = v.value
