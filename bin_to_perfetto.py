#!env python3

import argparse
from lib.emit_trace import emit_trace
from lib.perfetto_writer import PerfettoWriter
from lib.parse_bin_trace import parse_bin_trace
from lib.parse_to_trace import parse_to_trace


def main():
    parser = argparse.ArgumentParser(
        description="Transform a binary trace to a perfetto trace."
    )
    parser.add_argument("filename", type=str, help="The filename of the binary trace")
    parser.add_argument(
        "-o",
        "--out",
        type=str,
        help="The output filename (Perfetto trace)",
        default="out.perfetto-trace",
    )
    args = parser.parse_args()

    parse_items = parse_bin_trace(args.filename)
    print("parsing...")
    trace = parse_to_trace(parse_items)
    writer = PerfettoWriter()
    print("emitting...")
    emit_trace(trace, writer)
    print("writing...")
    writer.write(args.out)


if __name__ == "__main__":
    main()
