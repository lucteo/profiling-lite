from enum import Enum, auto
import struct
import lib.parse_dto as dto


class PacketType(Enum):
    free = 0
    init = 16
    static_string = auto()
    location = auto()

    stack = auto()
    thread_name = auto()

    zone_start = auto()
    zone_end = auto()
    zone_dynamic_name = auto()
    zone_param_bool = auto()
    zone_param_int = auto()
    zone_param_uint = auto()
    zone_param_double = auto()
    zone_param_string = auto()
    zone_flow = auto()
    zone_flow_terminate = auto()
    zone_category = auto()

    counter_track = auto()
    counter_value_int = auto()
    counter_value_double = auto()


DepType = Enum("DepType", ["string", "location"])


class _InitPacket:
    def __init__(self, f):
        self.magic, self.version = _read_and_unpack("4sI", f)

    def dependencies(self):
        return []

    def provides(self):
        return []


class _StaticStringPacket:
    def __init__(self, f):
        self.string_id = _read_and_unpack("Q", f)[0]
        size = _read_and_unpack("H", f)[0]
        self.string = f.read(size).decode("utf-8")

    def dependencies(self):
        return []

    def provides(self):
        return [(DepType.string, self.string_id)]


class _LocationPacket:
    def __init__(self, f):
        self.loc_id, self.name_id, self.function_id, self.file_id, self.line = (
            _read_and_unpack("4QI", f)
        )

    def dependencies(self):
        return [
            (DepType.string, self.name_id),
            (DepType.string, self.function_id),
            (DepType.string, self.file_id),
        ]

    def provides(self):
        return [(DepType.location, self.loc_id)]


class _StackPacket:
    def __init__(self, f):
        self.begin, self.end, size = _read_and_unpack("QQH", f)
        self.name = f.read(size).decode("utf-8")

    def dependencies(self):
        return []

    def provides(self):
        return []


class _ThreadNamePacket:
    def __init__(self, f):
        self.tid, size = _read_and_unpack("QH", f)
        self.thread_name = f.read(size).decode("utf-8")

    def dependencies(self):
        return []

    def provides(self):
        return []


class _ZoneStartPacket:
    def __init__(self, f):
        self.stack_ptr, self.tid, self.timestamp, self.loc_id = _read_and_unpack(
            "4Q", f
        )

    def dependencies(self):
        return [(DepType.location, self.loc_id)]

    def provides(self):
        return []


class _ZoneEndPacket:
    def __init__(self, f):
        self.stack_ptr, self.timestamp = _read_and_unpack("QQ", f)

    def dependencies(self):
        return []

    def provides(self):
        return []


class _ZoneDynamicNamePacket:
    def __init__(self, f):
        self.stack_ptr, size = _read_and_unpack("QH", f)
        self.name = f.read(size).decode("utf-8")


class _ZoneParamBoolPacket:
    def __init__(self, f):
        self.stack_ptr, self.param_name_id, self.value = _read_and_unpack("QQB", f)

    def dependencies(self):
        return [(DepType.string, self.param_name_id)]

    def provides(self):
        return []


class _ZoneParamIntPacket:
    def __init__(self, f):
        self.stack_ptr, self.param_name_id, self.value = _read_and_unpack("QQq", f)

    def dependencies(self):
        return [(DepType.string, self.param_name_id)]

    def provides(self):
        return []


class _ZoneParamUIntPacket:
    def __init__(self, f):
        self.stack_ptr, self.param_name_id, self.value = _read_and_unpack("QQQ", f)

    def dependencies(self):
        return [(DepType.string, self.param_name_id)]

    def provides(self):
        return []


class _ZoneParamDoublePacket:
    def __init__(self, f):
        self.stack_ptr, self.param_name_id, self.value = _read_and_unpack("QQd", f)

    def dependencies(self):
        return [(DepType.string, self.param_name_id)]

    def provides(self):
        return []


class _ZoneParamStringPacket:
    def __init__(self, f):
        self.stack_ptr, self.param_name_id, size = _read_and_unpack("QQH", f)
        self.value = f.read(size).decode("utf-8")

    def dependencies(self):
        return [(DepType.string, self.param_name_id)]

    def provides(self):
        return []


class _ZoneFlowPacket:
    def __init__(self, f):
        self.stack_ptr, self.flowid = _read_and_unpack("QQ", f)

    def dependencies(self):
        return []

    def provides(self):
        return []


class _ZoneFlowTerminatePacket:
    def __init__(self, f):
        self.stack_ptr, self.flowid = _read_and_unpack("QQ", f)

    def dependencies(self):
        return []

    def provides(self):
        return []


class _ZoneCategoryPacket:
    def __init__(self, f):
        self.stack_ptr, self.category_name_id = _read_and_unpack("QQ", f)

    def dependencies(self):
        return [(DepType.string, self.category_name_id)]

    def provides(self):
        return []


class _CounterTrackPacket:
    def __init__(self, f):
        self.tid, size = _read_and_unpack("QH", f)
        self.track_name = f.read(size).decode("utf-8")


class _CounterValueIntPacket:
    def __init__(self, f):
        self.tid, self.timestamp, self.value = _read_and_unpack("QQq", f)

    def dependencies(self):
        return []

    def provides(self):
        return []


class _CounterValueDoublePacket:
    def __init__(self, f):
        self.tid, self.timestamp, self.value = _read_and_unpack("QQd", f)

    def dependencies(self):
        return []

    def provides(self):
        return []


def _read_and_unpack(format, f):
    size = struct.calcsize(format)
    data = f.read(size)
    if not data:
        return None
    return struct.unpack(format, data)


def _parse_packet(type, f):
    if type == PacketType.init:
        return _InitPacket(f)
    elif type == PacketType.static_string:
        return _StaticStringPacket(f)
    elif type == PacketType.location:
        return _LocationPacket(f)

    elif type == PacketType.stack:
        return _StackPacket(f)
    elif type == PacketType.thread_name:
        return _ThreadNamePacket(f)

    elif type == PacketType.zone_start:
        return _ZoneStartPacket(f)
    elif type == PacketType.zone_end:
        return _ZoneEndPacket(f)
    elif type == PacketType.zone_dynamic_name:
        return _ZoneDynamicNamePacket(f)
    elif type == PacketType.zone_param_bool:
        return _ZoneParamBoolPacket(f)
    elif type == PacketType.zone_param_int:
        return _ZoneParamIntPacket(f)
    elif type == PacketType.zone_param_uint:
        return _ZoneParamUIntPacket(f)
    elif type == PacketType.zone_param_double:
        return _ZoneParamDoublePacket(f)
    elif type == PacketType.zone_param_string:
        return _ZoneParamStringPacket(f)
    elif type == PacketType.zone_flow:
        return _ZoneFlowPacket(f)
    elif type == PacketType.zone_flow_terminate:
        return _ZoneFlowTerminatePacket(f)
    elif type == PacketType.zone_category:
        return _ZoneCategoryPacket(f)

    elif type == PacketType.counter_track:
        return _CounterTrackPacket(f)
    elif type == PacketType.counter_value_int:
        return _CounterValueIntPacket(f)
    elif type == PacketType.counter_value_double:
        return _CounterValueDoublePacket(f)

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
            strings[packet.string_id] = packet.string
        elif isinstance(packet, _LocationPacket):
            yield dto.Location(
                locid=packet.loc_id,
                name=_get_string(packet.name_id),
                function_name=_get_string(packet.function_id),
                file_name=_get_string(packet.file_id),
                line_number=packet.line,
            )

        elif isinstance(packet, _StackPacket):
            yield dto.Stack(begin=packet.begin, end=packet.end, name=packet.name)
        elif isinstance(packet, _ThreadNamePacket):
            yield dto.Thread(tid=packet.tid, thread_name=packet.thread_name)

        elif isinstance(packet, _ZoneStartPacket):
            yield dto.ZoneStart(
                stack_ptr=packet.stack_ptr,
                tid=packet.tid,
                timestamp=packet.timestamp,
                locid=packet.loc_id,
            )
        elif isinstance(packet, _ZoneEndPacket):
            yield dto.ZoneEnd(stack_ptr=packet.stack_ptr, timestamp=packet.timestamp)
        elif isinstance(packet, _ZoneParamBoolPacket):
            yield dto.ZoneParam(
                stack_ptr=packet.stack_ptr,
                name=_get_string(packet.param_name_id),
                value=packet.value,
            )
        elif isinstance(packet, _ZoneParamIntPacket):
            yield dto.ZoneParam(
                stack_ptr=packet.stack_ptr,
                name=_get_string(packet.param_name_id),
                value=packet.value,
            )
        elif isinstance(packet, _ZoneParamUIntPacket):
            yield dto.ZoneParam(
                stack_ptr=packet.stack_ptr,
                name=_get_string(packet.param_name_id),
                value=packet.value,
            )
        elif isinstance(packet, _ZoneParamDoublePacket):
            yield dto.ZoneParam(
                stack_ptr=packet.stack_ptr,
                name=_get_string(packet.param_name_id),
                value=packet.value,
            )
        elif isinstance(packet, _ZoneParamStringPacket):
            yield dto.ZoneParam(
                stack_ptr=packet.stack_ptr,
                name=_get_string(packet.param_name_id),
                value=packet.value,
            )
        elif isinstance(packet, _ZoneFlowPacket):
            yield dto.ZoneFlow(stack_ptr=packet.stack_ptr, flowid=packet.flowid)
        elif isinstance(packet, _ZoneFlowTerminatePacket):
            yield dto.ZoneFlowTerminate(
                stack_ptr=packet.stack_ptr, flowid=packet.flowid
            )
        elif isinstance(packet, _ZoneCategoryPacket):
            yield dto.ZoneCategory(
                stack_ptr=packet.stack_ptr,
                category_name=_get_string(packet.category_name_id),
            )

        elif isinstance(packet, _CounterTrackPacket):
            yield dto.CounterTrack(tid=packet.tid, name=_get_string(packet.track_name))
        elif isinstance(packet, _CounterValueIntPacket):
            yield dto.CounterValue(
                tid=packet.tid, timestamp=packet.timestamp, value=packet.value
            )
        elif isinstance(packet, _CounterValueDoublePacket):
            yield dto.CounterValue(
                tid=packet.tid, timestamp=packet.timestamp, value=packet.value
            )
        else:
            raise ValueError(f"Unknown packet {packet}")


def parse_bin_trace(filename):
    packets = _packet_generator(filename)
    packets = _ensure_ordering(packets)
    return _packets_to_dtos(packets)
