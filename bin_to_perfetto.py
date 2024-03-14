#!env python3

import argparse
from lib.perfetto_writer import PerfettoWriter
from lib.parse_bin_trace import parse_bin_trace
from lib.emit_trace import emit_trace
import cProfile


def run(filename, out):
    parse_items = parse_bin_trace(filename)
    emit_dtos = emit_trace(parse_items)
    writer = PerfettoWriter(out)
    for obj in emit_dtos:
        writer.add(obj)
    writer.close()


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

    run(args.filename, args.out)
    # cProfile.run(f'run("{args.filename}", "{args.out}")')


if __name__ == "__main__":
    main()
