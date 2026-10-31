"""
CCSDS Space Packet — primary header (6 octets) + user data field.

Implements the CCSDS Space Packet Protocol primary header bit layout used for
telemetry (TM) and telecommand (TC) at a level suitable for V&V unit tests
(pack/unpack, length checks, APID / sequence count).

Reference: CCSDS 133.0-B (Space Packet Protocol).
PUS and CSP are separate layers above/beside this; not implemented here.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import Enum, auto


class SpacePacketError(ValueError):
    """Raised when a buffer cannot be parsed as a valid Space Packet."""


class PacketType(Enum):
    TELEMETRY = auto()
    TELECOMMAND = auto()


class SequenceFlags(Enum):
    CONTINUATION = 0b00
    FIRST = 0b01
    LAST = 0b10
    UNSEGMENTED = 0b11


@dataclass(frozen=True)
class SpacePacketHeader:
    packet_type: PacketType = PacketType.TELEMETRY
    secondary_header_flag: bool = False
    apid: int = 0
    sequence_flags: SequenceFlags = SequenceFlags.UNSEGMENTED
    sequence_count: int = 0
    packet_data_length: int = 0  # (len(user_data) - 1) per CCSDS rule

    def __post_init__(self) -> None:
        if not 0 <= self.apid <= 0x7FF:
            raise ValueError(f"APID must be 11 bits (0..2047), got {self.apid}")
        if not 0 <= self.sequence_count <= 0x3FFF:
            raise ValueError(f"sequence_count must be 14 bits, got {self.sequence_count}")
        if not 0 <= self.packet_data_length <= 0xFFFF:
            raise ValueError(f"packet_data_length must be 16 bits, got {self.packet_data_length}")


@dataclass(frozen=True)
class SpacePacket:
    header: SpacePacketHeader
    user_data: bytes = b""

    @property
    def total_length(self) -> int:
        return 6 + len(self.user_data)

    def pack(self) -> bytes:
        word0 = (
            (0 << 13)  # version = 000
            | ((1 if self.header.packet_type == PacketType.TELECOMMAND else 0) << 12)
            | ((1 if self.header.secondary_header_flag else 0) << 11)
            | (self.header.apid & 0x7FF)
        )
        word1 = (
            ((self.header.sequence_flags.value & 0x3) << 14)
            | (self.header.sequence_count & 0x3FFF)
        )
        word2 = self.header.packet_data_length & 0xFFFF
        return struct.pack(">HHH", word0, word1, word2) + self.user_data

    @classmethod
    def unpack(cls, data: bytes) -> SpacePacket:
        if len(data) < 6:
            raise SpacePacketError(
                f"Space Packet primary header is 6 bytes; got {len(data)} bytes"
            )
        word0, word1, word2 = struct.unpack(">HHH", data[:6])
        version = (word0 >> 13) & 0x7
        if version != 0:
            raise SpacePacketError(f"Unsupported CCSDS version {version}, expected 0")

        packet_type = PacketType.TELECOMMAND if ((word0 >> 12) & 1) else PacketType.TELEMETRY
        secondary_header_flag = bool((word0 >> 11) & 1)
        apid = word0 & 0x7FF
        seq_flag_value = (word1 >> 14) & 0x3
        try:
            sequence_flags = SequenceFlags(seq_flag_value)
        except ValueError as exc:
            raise SpacePacketError(f"Invalid sequence flags: {seq_flag_value}") from exc
        sequence_count = word1 & 0x3FFF
        packet_data_length = word2

        expected_user_len = packet_data_length + 1
        user_data = data[6:]
        if len(user_data) < expected_user_len:
            raise SpacePacketError(
                "Truncated packet: header declares "
                f"{expected_user_len} user byte(s), buffer has {len(user_data)}"
            )
        user_data = user_data[:expected_user_len]

        header = SpacePacketHeader(
            packet_type=packet_type,
            secondary_header_flag=secondary_header_flag,
            apid=apid,
            sequence_flags=sequence_flags,
            sequence_count=sequence_count,
            packet_data_length=packet_data_length,
        )
        return cls(header=header, user_data=user_data)


def build_telemetry_packet(apid: int, sequence_count: int, user_data: bytes) -> SpacePacket:
    header = SpacePacketHeader(
        packet_type=PacketType.TELEMETRY,
        apid=apid,
        sequence_count=sequence_count,
        packet_data_length=max(len(user_data) - 1, 0),
    )
    return SpacePacket(header=header, user_data=user_data)
