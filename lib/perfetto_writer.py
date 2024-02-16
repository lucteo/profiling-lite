import perfetto_trace_pb2 as pb2
import lib.emit_dto as dto


class PerfettoWriter:
    """Knows how to write a perfetto trace file."""

    def __init__(self):
        self._trace = pb2.Trace()

    def write(self, filename):
        """Writes the trace to a file."""
        with open(filename, "wb") as f:
            f.write(self._trace.SerializeToString())

    def add(self, item):
        """Add an emit dto object to the trace."""
        if isinstance(item, dto.ProcessTrack):
            self.add_process_track(item)
        elif isinstance(item, dto.Thread):
            self.add_thread(item)
        elif isinstance(item, dto.CounterTrack):
            self.add_counter_track(item)
        elif isinstance(item, dto.Location):
            self.add_location(item)
        elif isinstance(item, dto.ZoneStart):
            self.add_zone_start(item)
        elif isinstance(item, dto.ZoneEnd):
            self.add_zone_end(item)
        elif isinstance(item, dto.CounterValue):
            self.add_counter_value(item)
        else:
            raise ValueError(f"Unknown object {item}")

    def add_process_track(self, p: dto.ProcessTrack):
        """Adds a thread track to the trace."""
        packet = self._trace.packet.add()
        packet.track_descriptor.uuid = p.track_uuid
        packet.track_descriptor.name = p.name
        packet.track_descriptor.process.pid = p.pid

    def add_thread(self, t: dto.Thread):
        """Adds a thread track to the trace."""
        packet = self._trace.packet.add()
        packet.track_descriptor.uuid = t.track_uuid
        packet.track_descriptor.thread.pid = (t.pid & 0x7FFFFFFF)
        packet.track_descriptor.thread.tid = (t.tid & 0x7FFFFFFF)
        packet.track_descriptor.thread.thread_name = t.thread_name

    def add_counter_track(self, t: dto.CounterTrack):
        """Adds a thread track to the trace."""
        packet = self._trace.packet.add()
        packet.track_descriptor.uuid = t.track_uuid
        packet.track_descriptor.name = t.name
        if t.parent_track != None:
            packet.track_descriptor.parent_uuid = t.parent_track
        packet.track_descriptor.counter.unit_name = "value"

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
        packet.trusted_packet_sequence_id = 0
        packet.track_event.type = pb2.TrackEvent.Type.TYPE_SLICE_BEGIN
        packet.track_event.track_uuid = z.track_uuid
        packet.track_event.name = z.name
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
                if isinstance(v, bool):
                    entry.bool_value = v
                elif isinstance(v, int):
                    entry.int_value = v
                elif isinstance(v, float):
                    entry.double_value = v
                else:
                    entry.string_value = v
        for id in z.flows:
            packet.track_event.flow_ids.append(id)
        for category in z.categories:
            packet.track_event.categories.append(category)

    def add_zone_end(self, z: dto.ZoneEnd):
        """Adds a zone end event to the trace."""
        packet = self._trace.packet.add()
        packet.timestamp = z.timestamp
        packet.trusted_packet_sequence_id = 0
        packet.track_event.type = pb2.TrackEvent.Type.TYPE_SLICE_END
        packet.track_event.track_uuid = z.track_uuid
        for id in z.flows:
            packet.track_event.flow_ids.append(id)

    def add_counter_value(self, v: dto.CounterValue):
        """Adds a counter value to the trace."""
        packet = self._trace.packet.add()
        packet.timestamp = v.timestamp
        packet.trusted_packet_sequence_id = 0
        packet.track_event.type = pb2.TrackEvent.Type.TYPE_COUNTER
        packet.track_event.track_uuid = v.track_uuid
        if isinstance(v.value, int):
            packet.track_event.counter_value = v.value
        elif isinstance(v.value, float):
            packet.track_event.double_counter_value = v.value
