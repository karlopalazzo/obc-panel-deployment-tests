import pytest

from satellite.telemetry.ccsds_space_packet import (
    PacketType,
    SequenceFlags,
    SpacePacket,
    SpacePacketError,
    SpacePacketHeader,
    build_telemetry_packet,
)


@pytest.mark.unit
def test_pack_unpack_roundtrip():
    packet = build_telemetry_packet(
        apid=0x42,
        sequence_count=7,
        user_data=b"\xde\xad",
    )
    restored = SpacePacket.unpack(packet.pack())
    assert restored.header.apid == 0x42
    assert restored.header.sequence_count == 7
    assert restored.header.packet_type == PacketType.TELEMETRY
    assert restored.header.sequence_flags == SequenceFlags.UNSEGMENTED
    assert restored.user_data == b"\xde\xad"


@pytest.mark.unit
def test_known_header_hex():
    packet = SpacePacket(
        header=SpacePacketHeader(
            packet_type=PacketType.TELEMETRY,
            apid=0x010,
            sequence_flags=SequenceFlags.UNSEGMENTED,
            sequence_count=1,
            packet_data_length=0,
        ),
        user_data=b"\x00",
    )
    assert packet.pack() == bytes.fromhex("0010c001000000")


@pytest.mark.unit
def test_truncated_buffer_raises():
    with pytest.raises(SpacePacketError, match="6 bytes"):
        SpacePacket.unpack(b"\x00\x00")


@pytest.mark.unit
def test_truncated_user_data_raises():
    header_only = SpacePacket(
        header=SpacePacketHeader(packet_data_length=3),
        user_data=b"\x01",
    ).pack()[:6]
    payload = b"\x01\x02"
    with pytest.raises(SpacePacketError, match="Truncated packet"):
        SpacePacket.unpack(header_only + payload)


@pytest.mark.unit
def test_invalid_apid_on_build_raises():
    with pytest.raises(ValueError, match="APID"):
        SpacePacketHeader(apid=0x800)
