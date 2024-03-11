#!env python3

import argparse
from lib.perfetto_writer import PerfettoWriter
from lib.parse_text_trace import parse_text_trace
from lib.parse_to_trace import parse_to_trace, emit_trace


def main():
    parser = argparse.ArgumentParser(
        description="Transform a textual trace to a perfetto trace."
    )
    parser.add_argument("filename", type=str, help="The filename of the text trace")
    parser.add_argument(
        "-o",
        "--out",
        type=str,
        help="The output filename (Perfetto trace)",
        default="out.perfetto-trace",
    )
    args = parser.parse_args()

    parse_items = parse_text_trace(args.filename)
    trace = parse_to_trace(parse_items)
    writer = PerfettoWriter()
    emit_trace(trace, writer)
    writer.write(args.out)


if __name__ == "__main__":
    main()
