#!env python3

from lib.emit_trace import emit_trace
from lib.perfetto_writer import PerfettoWriter
from lib.parse_text_trace import parse_text_trace
from lib.parse_to_trace import parse_to_trace

parse_items = parse_text_trace("sample.text-trace")
trace = parse_to_trace(parse_items)
writer = PerfettoWriter()
emit_trace(trace, writer)
writer.write("out.perfetto-trace")
