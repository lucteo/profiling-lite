#!env python3

import argparse
from lib.perfetto_writer import PerfettoWriter
from lib.parse_text_trace import parse_text_trace
from lib.emit_trace import emit_trace


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
    emit_dtos = emit_trace(parse_items)
    writer = PerfettoWriter(args.out)
    for obj in emit_dtos:
        writer.add(obj)
    writer.close()


if __name__ == "__main__":
    main()
