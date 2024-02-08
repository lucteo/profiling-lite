#!env python3

from lib.perfetto_writer import PerfettoWriter
from lib.parse_text_trace import parse_text_trace
import lib.dto as dto

trace = PerfettoWriter()
for item in parse_text_trace("sample.text-trace"):
    print(item)
    if isinstance(item, dto.Thread):
        trace.add_thread(item)
    elif isinstance(item, dto.CounterTrack):
        trace.add_counter_track(item)
    elif isinstance(item, dto.ZoneStart):
        trace.add_zone_start(item)
    elif isinstance(item, dto.ZoneEnd):
        trace.add_zone_end(item)
    elif isinstance(item, dto.CounterValue):
        trace.add_counter_value(item)

trace.write("out.perfetto-trace")
