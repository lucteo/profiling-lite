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


class _Csv_THREAD:
    def __init__(self, args):
        assert len(args) == 2, f"THREAD expects 2 arguments, got: {args}"
        self.tid = int(args[0])
        self.thread_name = args[1]


class _Csv_COUNTERTRACK:
    def __init__(self, args):
        assert len(args) == 2, f"COUNTERTRACK expects 2 arguments, got: {args}"
        self.tid = int(args[0])
        self.name = args[1]


class _Csv_LOCATION:
    def __init__(self, args):
        assert len(args) == 5, f"LOCATION expects 5 arguments, got: {args}"
        self.locid = int(args[0])
        self.name = args[1]
        self.function_name = args[2]
        self.file = args[3]
        self.line = int(args[4])


class _Csv_ZONE_START:
    def __init__(self, args):
        assert len(args) == 3, f"ZONE_START expects 3 arguments, got: {args}"
        self.tid = int(args[0])
        self.timestamp = int(args[1])
        self.locid = int(args[2])


class _Csv_ZONE_END:
    def __init__(self, args):
        assert len(args) == 2, f"ZONE_END expects 2 arguments, got: {args}"
        self.tid = int(args[0])
        self.timestamp = int(args[1])


class _Csv_ZONE_NAME:
    def __init__(self, args):
        assert len(args) == 2, f"ZONE_NAME expects 2 arguments, got: {args}"
        self.tid = int(args[0])
        self.name = args[1]


class _Csv_ZONE_PARAM:
    def __init__(self, args):
        assert len(args) == 3, f"ZONE_PARAM expects 3 arguments, got: {args}"
        self.tid = int(args[0])
        self.name = args[1]
        self.value = args[2]


class _Csv_ZONE_FLOW:
    def __init__(self, args):
        assert len(args) == 2, f"ZONE_FLOW expects 2 arguments, got: {args}"
        self.tid = int(args[0])
        self.flowid = int(args[1])


class _Csv_ZONE_CATEGORY:
    def __init__(self, args):
        assert len(args) == 2, f"ZONE_CATEGORY expects 2 arguments, got: {args}"
        self.tid = int(args[0])
        self.category_name = args[1]


class _Csv_COUNTERVALUE:
    def __init__(self, args):
        assert len(args) == 3, f"COUNTERVALUE expects 3 arguments, got: {args}"
        self.tid = int(args[0])
        self.timestamp = int(args[1])
        self.value = int(args[2])


class _Csv_THREAD_SWITCH_START:
    def __init__(self, args):
        assert len(args) == 2, f"THREAD_SWITCH_START expects 2 arguments, got: {args}"
        self.tid = int(args[0])
        self.id = int(args[1])


class _Csv_THREAD_SWITCH_END:
    def __init__(self, args):
        assert len(args) == 3, f"THREAD_SWITCH_END expects 3 arguments, got: {args}"
        self.tid = int(args[0])
        self.timestamp = int(args[1])
        self.id = int(args[2])


class _Csv_SPAWN:
    def __init__(self, args):
        assert len(args) == 4, f"SPAWN expects 4 arguments, got: {args}"
        self.spawn_id = int(args[0])
        self.tid = int(args[1])
        self.timestamp = int(args[2])
        self.num_threads = int(args[3])


class _Csv_SPAWN_CONTINUE:
    def __init__(self, args):
        assert len(args) == 3, f"SPAWN_CONTINUE expects 2 arguments, got: {args}"
        self.spawn_id = int(args[0])
        self.tid = int(args[1])
        self.timestamp = int(args[2])


class _Csv_SPAWN_ENDING:
    def __init__(self, args):
        assert len(args) == 3, f"SPAWN_ENDING expects 2 arguments, got: {args}"
        self.spawn_id = int(args[0])
        self.tid = int(args[1])
        self.timestamp = int(args[2])


class _Csv_SPAWN_DONE:
    def __init__(self, args):
        assert len(args) == 3, f"SPAWN_DONE expects 2 arguments, got: {args}"
        self.spawn_id = int(args[0])
        self.tid = int(args[1])
        self.timestamp = int(args[2])


def _csv_rows_to_objects(rows):
    commands = [
        "THREAD",
        "COUNTERTRACK",
        "LOCATION",
        "ZONE_START",
        "ZONE_END",
        "ZONE_NAME",
        "ZONE_PARAM",
        "ZONE_FLOW",
        "ZONE_CATEGORY",
        "COUNTERVALUE",
        "THREAD_SWITCH_START",
        "THREAD_SWITCH_END",
        "SPAWN",
        "SPAWN_CONTINUE",
        "SPAWN_ENDING",
        "SPAWN_DONE",
    ]
    for row in rows:
        command = row[0].upper()
        args = row[1:]

        if command in commands:
            class_name = f"_Csv_{command}"
            yield globals()[class_name](args)
        else:
            raise ValueError(f"Unknown command {command}")


def _csv_objects_to_parse_dto(objects):
    for obj in objects:
        if isinstance(obj, _Csv_THREAD):
            yield dto.Thread(tid=obj.tid, thread_name=obj.thread_name)
        elif isinstance(obj, _Csv_COUNTERTRACK):
            yield dto.CounterTrack(tid=obj.tid, name=obj.name)

        elif isinstance(obj, _Csv_LOCATION):
            yield dto.Location(
                locid=obj.locid,
                name=obj.name,
                function_name=obj.function_name,
                file_name=obj.file,
                line_number=obj.line,
            )

        elif isinstance(obj, _Csv_ZONE_START):
            yield dto.ZoneStart(tid=obj.tid, timestamp=obj.timestamp, locid=obj.locid)
        elif isinstance(obj, _Csv_ZONE_END):
            yield dto.ZoneEnd(tid=obj.tid, timestamp=obj.timestamp)
        elif isinstance(obj, _Csv_ZONE_NAME):
            yield dto.ZoneName(tid=obj.tid, name=obj.name)
        elif isinstance(obj, _Csv_ZONE_PARAM):
            yield dto.ZoneParam(tid=obj.tid, name=obj.name, value=obj.value)
        elif isinstance(obj, _Csv_ZONE_FLOW):
            yield dto.ZoneFlow(tid=obj.tid, flowid=obj.flowid)
        elif isinstance(obj, _Csv_ZONE_CATEGORY):
            yield dto.ZoneCategory(tid=obj.tid, category_name=obj.category_name)

        elif isinstance(obj, _Csv_COUNTERVALUE):
            yield dto.CounterValue(obj.tid, obj.timestamp, obj.value)

        elif isinstance(obj, _Csv_THREAD_SWITCH_START):
            yield dto.ThreadSwitchStart(obj.tid, obj.id)
        elif isinstance(obj, _Csv_THREAD_SWITCH_END):
            yield dto.ThreadSwitchEnd(obj.tid, obj.timestamp, obj.id)

        elif isinstance(obj, _Csv_SPAWN):
            yield dto.Spawn(obj.spawn_id, obj.tid, obj.timestamp, obj.num_threads)
        elif isinstance(obj, _Csv_SPAWN_CONTINUE):
            yield dto.SpawnContinue(obj.spawn_id, obj.tid, obj.timestamp)
        elif isinstance(obj, _Csv_SPAWN_ENDING):
            yield dto.SpawnEnding(obj.spawn_id, obj.tid, obj.timestamp)
        elif isinstance(obj, _Csv_SPAWN_DONE):
            yield dto.SpawnDone(obj.spawn_id, obj.tid, obj.timestamp)

        else:
            raise ValueError(f"Unknown object {obj}")


def parse_text_trace(filename):
    r = _lines_in_file(filename)
    r = _content_lines(r)
    r = _csv_rows(r)
    r = _csv_rows_to_objects(r)
    r = _csv_objects_to_parse_dto(r)
    return r
