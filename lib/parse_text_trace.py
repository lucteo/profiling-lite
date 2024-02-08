import csv
import lib.dto as dto


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


class _Parse_THREAD:
    def __init__(self, args):
        assert len(args) == 2, f"THREAD expects 2 arguments, got: {args}"
        self.tid = int(args[0])
        self.thread_name = args[1]


class _Parse_COUNTERTRACK:
    def __init__(self, args):
        assert len(args) == 2, f"COUNTERTRACK expects 2 arguments, got: {args}"
        self.tid = int(args[0])
        self.name = args[1]


class _Parse_LOCATION:
    def __init__(self, args):
        assert len(args) == 5, f"LOCATION expects 5 arguments, got: {args}"
        self.locid = int(args[0])
        self.name = args[1]
        self.function_name = args[2]
        self.file = args[3]
        self.line = int(args[4])


class _Parse_ZBEGIN:
    def __init__(self, args):
        assert len(args) == 3, f"ZBEGIN expects 3 arguments, got: {args}"
        self.tid = int(args[0])
        self.timestamp = int(args[1])
        self.locid = int(args[2])


class _Parse_ZEND:
    def __init__(self, args):
        assert len(args) == 2, f"ZEND expects 2 arguments, got: {args}"
        self.tid = int(args[0])
        self.timestamp = int(args[1])


class _Parse_ZPARAM:
    def __init__(self, args):
        assert len(args) == 3, f"ZPARAM expects 3 arguments, got: {args}"
        self.tid = int(args[0])
        self.name = args[1]
        self.value = args[2]


class _Parse_ZNAME:
    def __init__(self, args):
        assert len(args) == 2, f"ZNAME expects 2 arguments, got: {args}"
        self.tid = int(args[0])
        self.text = args[1]


class _Parse_ZFLOW:
    def __init__(self, args):
        assert len(args) == 2, f"ZFLOW expects 2 arguments, got: {args}"
        self.tid = int(args[0])
        self.flowid = int(args[1])


class _Parse_ZCATEGORY:
    def __init__(self, args):
        assert len(args) == 2, f"ZCATEGORY expects 2 arguments, got: {args}"
        self.tid = int(args[0])
        self.category_name = args[1]


class _Parse_COUNTERVALUE:
    def __init__(self, args):
        assert len(args) == 3, f"COUNTERVALUE expects 3 arguments, got: {args}"
        self.tid = int(args[0])
        self.timestamp = int(args[1])
        self.value = int(args[2])


def _csv_to_parse_objects(rows):
    for row in rows:
        command = row[0].upper()
        args = row[1:]

        if command == "THREAD":
            yield _Parse_THREAD(args)

        elif command == "COUNTERTRACK":
            yield _Parse_COUNTERTRACK(args)

        elif command == "LOCATION":
            yield _Parse_LOCATION(args)

        elif command == "ZBEGIN":
            yield _Parse_ZBEGIN(args)

        elif command == "ZEND":
            yield _Parse_ZEND(args)

        elif command == "ZPARAM":
            yield _Parse_ZPARAM(args)

        elif command == "ZNAME":
            yield _Parse_ZNAME(args)

        elif command == "ZFLOW":
            yield _Parse_ZFLOW(args)

        elif command == "ZCATEGORY":
            yield _Parse_ZCATEGORY(args)

        elif command == "COUNTERVALUE":
            yield _Parse_COUNTERVALUE(args)

        else:
            raise ValueError(f"Unknown command {command}")


def _dto_location(l):
    return dto.Location(
        locid=l.locid,
        name=l.name,
        function_name=l.function_name,
        file_name=l.file,
        line_number=l.line,
    )


def _dto_zone_start(zone):
    return dto.ZoneStart(ref=zone)


def _dto_zone_end(zone):
    return dto.ZoneEnd(ref=zone)


def _parse_objects_to_dto(objects):
    threads = {}
    locations = {}
    open_zones_per_thread = {}  # tid -> list of zones

    for obj in objects:
        if isinstance(obj, _Parse_THREAD):
            threads[obj.tid] = obj
            yield dto.Thread(obj.tid, obj.thread_name)

        elif isinstance(obj, _Parse_COUNTERTRACK):
            yield dto.CounterTrack(obj.tid, obj.name)

        elif isinstance(obj, _Parse_LOCATION):
            location = _dto_location(obj)
            locations[obj.locid] = location
            yield location

        elif isinstance(obj, _Parse_ZBEGIN):
            zone = dto.Zone(
                obj.tid,
                obj.timestamp,
                0,
                locations[obj.locid],
                locations[obj.locid].name,
            )
            if obj.tid not in open_zones_per_thread:
                open_zones_per_thread[obj.tid] = []
            open_zones = open_zones_per_thread[obj.tid]
            open_zones.append(zone)
            yield _dto_zone_start(zone)

        elif isinstance(obj, _Parse_ZEND):
            zone = open_zones_per_thread[obj.tid].pop()
            zone.end = obj.timestamp
            yield _dto_zone_end(zone)

        elif isinstance(obj, _Parse_ZPARAM):
            zone = open_zones_per_thread[obj.tid][-1]
            zone.params[obj.name] = obj.value

        elif isinstance(obj, _Parse_ZNAME):
            zone = open_zones_per_thread[obj.tid][-1]
            zone.name = obj.text

        elif isinstance(obj, _Parse_ZFLOW):
            zone = open_zones_per_thread[obj.tid][-1]
            zone.flows.append(obj.flowid)

        elif isinstance(obj, _Parse_ZCATEGORY):
            zone = open_zones_per_thread[obj.tid][-1]
            zone.categories.append(obj.category_name)

        elif isinstance(obj, _Parse_COUNTERVALUE):
            yield dto.CounterValue(obj.tid, obj.timestamp, obj.value)

        else:
            raise ValueError(f"Unknown object {obj}")


def _defer_zone_starts(dto_objects):
    thread_has_deferred_zone_start = {}  # tid -> bool

    def _check_deferred_zone_start(tid):
        deferred = thread_has_deferred_zone_start.get(tid, None)
        if deferred:
            yield deferred
            thread_has_deferred_zone_start[tid] = None

    for obj in dto_objects:
        if isinstance(obj, dto.ZoneStart):
            yield from _check_deferred_zone_start(obj.ref.tid)
            thread_has_deferred_zone_start[obj.ref.tid] = obj

        elif isinstance(obj, dto.ZoneEnd):
            yield from _check_deferred_zone_start(obj.ref.tid)
            yield obj
        else:
            yield obj


def parse_text_trace(filename):
    r = _lines_in_file(filename)
    r = _content_lines(r)
    r = _csv_rows(r)
    r = _csv_to_parse_objects(r)
    r = _parse_objects_to_dto(r)
    r = _defer_zone_starts(r)
    return r
