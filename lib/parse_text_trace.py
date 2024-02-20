import csv
import lib.parse_dto as dto


def _lines_in_file(filename):
    with open(filename, "r") as file:
        for line in file.readlines():
            yield line.strip()


def _content_lines(lines):
    for line in lines:
        if line == "":
            continue
        if line.startswith("#"):
            continue
        yield line


def _csv_rows(lines):
    return csv.reader(
        lines, delimiter=",", quotechar='"', skipinitialspace=True, strict=True
    )


def _parse_STACK(args):
    assert len(args) == 3, f"STACK expects 2 arguments, got: {args}"
    return dto.Stack(begin=int(args[0]), end=int(args[1]), name=args[2])


def _parse_THREAD(args):
    assert len(args) == 2, f"THREAD expects 2 arguments, got: {args}"
    return dto.Thread(tid=int(args[0]), thread_name=args[1])


def _parse_LOCATION(args):
    assert len(args) == 5, f"LOCATION expects 5 arguments, got: {args}"
    return dto.Location(
        locid=int(args[0]),
        name=args[1],
        function_name=args[2],
        file_name=args[3],
        line_number=int(args[4]),
    )


def _parse_ZONE_START(args):
    assert len(args) == 4, f"ZONE_START expects 4 arguments, got: {args}"
    return dto.ZoneStart(
        stack_ptr=int(args[0]),
        tid=int(args[1]),
        timestamp=int(args[2]),
        locid=int(args[3]),
    )


def _parse_ZONE_END(args):
    assert len(args) == 2, f"ZONE_END expects 2 arguments, got: {args}"
    return dto.ZoneEnd(stack_ptr=int(args[0]), timestamp=int(args[1]))


def _parse_ZONE_NAME(args):
    assert len(args) == 2, f"ZONE_NAME expects 2 arguments, got: {args}"
    return dto.ZoneName(stack_ptr=int(args[0]), name=args[1])


def _parse_ZONE_PARAM(args):
    assert len(args) == 3, f"ZONE_PARAM expects 3 arguments, got: {args}"
    return dto.ZoneParam(stack_ptr=int(args[0]), name=args[1], value=args[2])


def _parse_ZONE_FLOW(args):
    assert len(args) == 2, f"ZONE_FLOW expects 2 arguments, got: {args}"
    return dto.ZoneFlow(stack_ptr=int(args[0]), flowid=int(args[1]))


def _parse_ZONE_FLOW_T(args):
    assert len(args) == 2, f"ZONE_FLOW_T expects 2 arguments, got: {args}"
    return dto.ZoneFlowTerminate(stack_ptr=int(args[0]), flowid=int(args[1]))


def _parse_ZONE_CATEGORY(args):
    assert len(args) == 2, f"ZONE_CATEGORY expects 2 arguments, got: {args}"
    return dto.ZoneCategory(stack_ptr=int(args[0]), category_name=args[1])


def _parse_COUNTER_TRACK(args):
    assert len(args) == 2, f"COUNTER_TRACK expects 2 arguments, got: {args}"
    return dto.CounterTrack(tid=int(args[0]), name=args[1])


def _parse_COUNTER_VALUE(args):
    assert len(args) == 3, f"COUNTER_VALUE expects 3 arguments, got: {args}"
    return dto.CounterValue(
        tid=int(args[0]), timestamp=int(args[1]), value=int(args[2])
    )


def _csv_rows_to_objects(rows):
    commands = [
        "STACK",
        "THREAD",
        "LOCATION",
        "ZONE_START",
        "ZONE_END",
        "ZONE_NAME",
        "ZONE_PARAM",
        "ZONE_FLOW",
        "ZONE_FLOW_T",
        "ZONE_CATEGORY",
        "COUNTER_TRACK",
        "COUNTER_VALUE",
    ]
    for row in rows:
        command = row[0].upper()
        args = row[1:]

        if command in commands:
            fun_name = f"_parse_{command}"
            yield globals()[fun_name](args)
        else:
            raise ValueError(f"Unknown command {command}")


def parse_text_trace(filename):
    r = _lines_in_file(filename)
    r = _content_lines(r)
    r = _csv_rows(r)
    r = _csv_rows_to_objects(r)
    return r
