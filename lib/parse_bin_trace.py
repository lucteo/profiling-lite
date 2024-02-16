from enum import Enum, auto
import struct
import lib.parse_dto as dto


class PacketType(Enum):
    free = 0
    init = 16
    static_string = auto()
    location = auto()
    thread_name = auto()
    counter_track = auto()
    zone_start = auto()
    zone_end = auto()
    zone_dynamic_name = auto()
    zone_param_bool = auto()
    zone_param_int = auto()
    zone_param_uint = auto()
    zone_param_double = auto()
    zone_param_string = auto()
    zone_flow = auto()
    zone_category = auto()
    counter_value_int = auto()
    counter_value_double = auto()
    thread_switch_start = auto()
    thread_switch_end = auto()
    spawn = auto()
    spawn_continue = auto()
    spawn_ending = auto()
    spawn_done = auto()


DepType = Enum("DepType", ["string", "location"])


class _InitPacket:
    def __init__(self, tuple):
        self.magic, self.version = tuple

    def dependencies(self):
        return []

    def provides(self):
        return []


class _LocationPacket:
    def __init__(self, tuple):
        self.loc_id, self.name_id, self.function_id, self.file_id, self.line = tuple

    def dependencies(self):
        return [
            (DepType.string, self.name_id),
            (DepType.string, self.function_id),
            (DepType.string, self.file_id),
        ]

    def provides(self):
        return [(DepType.location, self.loc_id)]


class _ZoneStartPacket:
    def __init__(self, tuple):
        self.tid, self.timestamp, self.loc_id = tuple

    def dependencies(self):
        return [(DepType.location, self.loc_id)]

    def provides(self):
        return []


class _ZoneEndPacket:
    def __init__(self, tuple):
        self.tid, self.timestamp = tuple

    def dependencies(self):
        return []

    def provides(self):
        return []


class _ZoneParamBoolPacket:
    def __init__(self, tuple):
        self.tid, self.param_name_id, self.value = tuple

    def dependencies(self):
        return [(DepType.string, self.param_name_id)]

    def provides(self):
        return []


class _ZoneParamIntPacket:
    def __init__(self, tuple):
        self.tid, self.param_name_id, self.value = tuple

    def dependencies(self):
        return [(DepType.string, self.param_name_id)]

    def provides(self):
        return []


class _ZoneParamUIntPacket:
    def __init__(self, tuple):
        self.tid, self.param_name_id, self.value = tuple

    def dependencies(self):
        return [(DepType.string, self.param_name_id)]

    def provides(self):
        return []


class _ZoneParamDoublePacket:
    def __init__(self, tuple):
        self.tid, self.param_name_id, self.value = tuple

    def dependencies(self):
        return [(DepType.string, self.param_name_id)]

    def provides(self):
        return []


class _ZoneFlowPacket:
    def __init__(self, tuple):
        self.tid, self.flowid = tuple

    def dependencies(self):
        return []

    def provides(self):
        return []


class _ZoneFlowCategoryPacket:
    def __init__(self, tuple):
        self.tid, self.category_name_id = tuple

    def dependencies(self):
        return [(DepType.string, self.category_name_id)]

    def provides(self):
        return []


class _CounterValueIntPacket:
    def __init__(self, tuple):
        self.tid, self.timestamp, self.value = tuple

    def dependencies(self):
        return []

    def provides(self):
        return []


class _CounterValueDoublePacket:
    def __init__(self, tuple):
        self.tid, self.timestamp, self.value = tuple

    def dependencies(self):
        return []

    def provides(self):
        return []


class _ThreadSwitchStartPacket:
    def __init__(self, tuple):
        self.tid, self.switch_id = tuple

    def dependencies(self):
        return []

    def provides(self):
        return []


class _ThreadSwitchEndPacket:
    def __init__(self, tuple):
        self.tid, self.timestamp, self.switch_id = tuple

    def dependencies(self):
        return []

    def provides(self):
        return []


class _SpawnPacket:
    def __init__(self, tuple):
        self.spawn_id, self.tid, self.timestamp, self.num_threads = tuple

    def dependencies(self):
        return []

    def provides(self):
        return []


class _SpawnContinuePacket:
    def __init__(self, tuple):
        self.spawn_id, self.tid, self.timestamp = tuple

    def dependencies(self):
        return []

    def provides(self):
        return []


class _SpawnEndingPacket:
    def __init__(self, tuple):
        self.spawn_id, self.tid, self.timestamp = tuple

    def dependencies(self):
        return []

    def provides(self):
        return []


class _SpawnDonePacket:
    def __init__(self, tuple):
        self.spawn_id, self.tid, self.timestamp = tuple

    def dependencies(self):
        return []

    def provides(self):
        return []


# Dynamic packet types


class _StaticStringPacket:
    def __init__(self, f):
        self.string_id = _read_and_unpack("Q", f)[0]
        size = _read_and_unpack("H", f)[0]
        self.string = f.read(size).decode("utf-8")

    def dependencies(self):
        return []

    def provides(self):
        return [(DepType.string, self.string_id)]


class _ThreadNamePacket:
    def __init__(self, f):
        self.tid, size = _read_and_unpack("QH", f)
        self.thread_name = f.read(size).decode("utf-8")

    def dependencies(self):
        return []

    def provides(self):
        return []


class _CounterTrackPacket:
    def __init__(self, f):
        self.tid, size = _read_and_unpack("QH", f)
        self.track_name = f.read(size).decode("utf-8")


class _ZoneDynamicNamePacket:
    def __init__(self, f):
        self.tid, size = _read_and_unpack("QH", f)
        self.name = f.read(size).decode("utf-8")


class _ZoneParamStringPacket:
    def __init__(self, f):
        self.tid, self.param_name_id, size = _read_and_unpack("QQH", f)
        self.value = f.read(size).decode("utf-8")

    def dependencies(self):
        return [(DepType.string, self.param_name_id)]

    def provides(self):
        return []


static_packet_formats = {
    PacketType.init: "4sI",
    PacketType.location: "4QI",
    PacketType.zone_start: "3Q",
    PacketType.zone_end: "2Q",
    PacketType.zone_param_bool: "QQB",
    PacketType.zone_param_int: "QQq",
    PacketType.zone_param_uint: "QQQ",
    PacketType.zone_param_double: "QQd",
    PacketType.zone_flow: "QQ",
    PacketType.zone_category: "QQ",
    PacketType.counter_value_int: "QQq",
    PacketType.counter_value_double: "QQd",
    PacketType.thread_switch_start: "QQ",
    PacketType.thread_switch_end: "QQQ",
    PacketType.spawn: "QQQB",
    PacketType.spawn_continue: "QQQ",
    PacketType.spawn_ending: "QQQ",
    PacketType.spawn_done: "QQQ",
}


def _read_and_unpack(format, f):
    size = struct.calcsize(format)
    data = f.read(size)
    if not data:
        return None
    return struct.unpack(format, data)


def _parse_packet(type, f):
    if type in static_packet_formats:
        format = static_packet_formats[type]
        tuple = _read_and_unpack(format, f)
        if type == PacketType.init:
            return _InitPacket(tuple)
        elif type == PacketType.location:
            return _LocationPacket(tuple)
        elif type == PacketType.zone_start:
            return _ZoneStartPacket(tuple)
        elif type == PacketType.zone_end:
            return _ZoneEndPacket(tuple)
        elif type == PacketType.zone_param_bool:
            return _ZoneParamBoolPacket(tuple)
        elif type == PacketType.zone_param_int:
            return _ZoneParamIntPacket(tuple)
        elif type == PacketType.zone_param_uint:
            return _ZoneParamUIntPacket(tuple)
        elif type == PacketType.zone_param_double:
            return _ZoneParamDoublePacket(tuple)
        elif type == PacketType.zone_flow:
            return _ZoneFlowPacket(tuple)
        elif type == PacketType.zone_category:
            return _ZoneFlowCategoryPacket(tuple)
        elif type == PacketType.counter_value_int:
            return _CounterValueIntPacket(tuple)
        elif type == PacketType.counter_value_double:
            return _CounterValueDoublePacket(tuple)
        elif type == PacketType.thread_switch_start:
            return _ThreadSwitchStartPacket(tuple)
        elif type == PacketType.thread_switch_end:
            return _ThreadSwitchEndPacket(tuple)
        elif type == PacketType.spawn:
            return _SpawnPacket(tuple)
        elif type == PacketType.spawn_continue:
            return _SpawnContinuePacket(tuple)
        elif type == PacketType.spawn_ending:
            return _SpawnEndingPacket(tuple)
        elif type == PacketType.spawn_done:
            return _SpawnDonePacket(tuple)
        else:
            raise ValueError(f"Unknown static packet type {type}")
    elif type == PacketType.static_string:
        return _StaticStringPacket(f)
    elif type == PacketType.thread_name:
        return _ThreadNamePacket(f)
    elif type == PacketType.counter_track:
        return _CounterTrackPacket(f)
    elif type == PacketType.zone_dynamic_name:
        return _ZoneDynamicNamePacket(f)
    elif type == PacketType.zone_param_string:
        return _ZoneParamStringPacket(f)
    elif type == PacketType.free:
        return None
    else:
        raise ValueError(f"Unknown packet type {type}")


def _parse_next_packet(f):
    tuple = _read_and_unpack("B", f)
    if tuple == None:
        return None
    type = PacketType(tuple[0])
    return _parse_packet(type, f)


def _packet_generator(filename):
    with open(filename, "rb") as file:
        while True:
            p = _parse_next_packet(file)
            if not p:
                break
            yield p


def _ensure_ordering(packets):
    # For each packet, check the list of dependencies. If we've already seen the dependency yield the packet, otherwise delay it.
    # If we've delayed a packet and we've seen all of its dependencies, yield it and all other delayed packets.
    seen = set()
    unseen_dependencies = set()
    delayed_packets = []
    delayed_locations = []
    for packet in packets:
        # Update what we seen with the provides of the packet.
        provides = set(packet.provides())
        seen.update(provides)
        unseen_dependencies.difference_update(provides)

        # Now, check the dependencies of the packet.
        dependencies = set(packet.dependencies())
        unseen_dependencies.update(dependencies.difference(seen))

        if unseen_dependencies:
            if isinstance(packet, _StaticStringPacket):
                # Always yield strings.
                yield packet
            elif isinstance(packet, _LocationPacket):
                # Keep the locations serarate, we need to process them first.
                delayed_locations.append(packet)
            else:
                # The other packets that are delayed.
                delayed_packets.append(packet)
        elif delayed_packets:
            # This package solves all the dependencies of the delayed packets.
            yield packet
            for p in delayed_locations:
                yield p
            for p in delayed_packets:
                yield p
            delayed_locations = []
            delayed_packets = []
        else:
            yield packet

    assert not unseen_dependencies, f"Unresolved dependencies {unseen_dependencies}"
    assert not delayed_packets, f"Delayed packets {delayed_packets}"


def _packets_to_dtos(packets):
    strings = {}

    def _get_string(id):
        if id not in strings:
            strings[id] = ""
        return strings[id]

    for packet in packets:
        if isinstance(packet, _InitPacket):
            assert packet.magic == b"PROF"
            assert packet.version == 1
        elif isinstance(packet, _StaticStringPacket):
            strings[packet.string_id]  = packet.string
        elif isinstance(packet, _LocationPacket):
            yield dto.Location(
                locid=packet.loc_id,
                name=_get_string(packet.name_id),
                function_name=_get_string(packet.function_id),
                file_name=_get_string(packet.file_id),
                line_number=packet.line,
            )
        elif isinstance(packet, _ThreadNamePacket):
            yield dto.Thread(tid=packet.tid, thread_name=packet.thread_name)
        elif isinstance(packet, _CounterTrackPacket):
            yield dto.CounterTrack(tid=packet.tid, name=_get_string(packet.track_name))
        elif isinstance(packet, _ZoneStartPacket):
            yield dto.ZoneStart(
                tid=packet.tid, timestamp=packet.timestamp, locid=packet.loc_id
            )
        elif isinstance(packet, _ZoneEndPacket):
            yield dto.ZoneEnd(tid=packet.tid, timestamp=packet.timestamp)
        elif isinstance(packet, _ZoneParamBoolPacket):
            yield dto.ZoneParam(
                tid=packet.tid,
                name=_get_string(packet.param_name_id),
                value=packet.value,
            )
        elif isinstance(packet, _ZoneParamIntPacket):
            yield dto.ZoneParam(
                tid=packet.tid,
                name=_get_string(packet.param_name_id),
                value=packet.value,
            )
        elif isinstance(packet, _ZoneParamUIntPacket):
            yield dto.ZoneParam(
                tid=packet.tid,
                name=_get_string(packet.param_name_id),
                value=packet.value,
            )
        elif isinstance(packet, _ZoneParamDoublePacket):
            yield dto.ZoneParam(
                tid=packet.tid,
                name=_get_string(packet.param_name_id),
                value=packet.value,
            )
        elif isinstance(packet, _ZoneParamStringPacket):
            yield dto.ZoneParam(
                tid=packet.tid,
                name=_get_string(packet.param_name_id),
                value=packet.value,
            )
        elif isinstance(packet, _ZoneFlowPacket):
            yield dto.ZoneFlow(tid=packet.tid, flowid=packet.flowid)
        elif isinstance(packet, _ZoneFlowCategoryPacket):
            yield dto.ZoneCategory(
                tid=packet.tid, category_name=_get_string(packet.category_name_id)
            )
        elif isinstance(packet, _CounterValueIntPacket):
            yield dto.CounterValue(
                tid=packet.tid, timestamp=packet.timestamp, value=packet.value
            )
        elif isinstance(packet, _CounterValueDoublePacket):
            yield dto.CounterValue(
                tid=packet.tid, timestamp=packet.timestamp, value=packet.value
            )
        elif isinstance(packet, _ThreadSwitchStartPacket):
            yield dto.ThreadSwitchStart(tid=packet.tid, id=packet.switch_id)
        elif isinstance(packet, _ThreadSwitchEndPacket):
            yield dto.ThreadSwitchEnd(
                tid=packet.tid, timestamp=packet.timestamp, id=packet.switch_id
            )
        elif isinstance(packet, _SpawnPacket):
            yield dto.Spawn(
                tid=packet.tid,
                spawn_id=packet.spawn_id,
                timestamp=packet.timestamp,
                num_threads=packet.num_threads,
            )
        elif isinstance(packet, _SpawnContinuePacket):
            yield dto.SpawnContinue(
                tid=packet.tid, spawn_id=packet.spawn_id, timestamp=packet.timestamp
            )
        elif isinstance(packet, _SpawnEndingPacket):
            yield dto.SpawnEnding(
                tid=packet.tid, spawn_id=packet.spawn_id, timestamp=packet.timestamp
            )
        elif isinstance(packet, _SpawnDonePacket):
            yield dto.SpawnDone(
                tid=packet.tid, spawn_id=packet.spawn_id, timestamp=packet.timestamp
            )
        else:
            raise ValueError(f"Unknown packet {packet}")


def parse_bin_trace(filename):
    packets = _packet_generator(filename)
    packets = _ensure_ordering(packets)
    return _packets_to_dtos(packets)
