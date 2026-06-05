from __future__ import annotations

from dataclasses import dataclass


PARAM_1 = 0x80
PARAM_2 = 0x40
PARAM_3 = 0x20


@dataclass(frozen=True)
class DecodedAudioOpcode:
    offset: int
    opcode: int
    name: str
    argument: int | None
    argument_kind: str


@dataclass(frozen=True)
class DecodeIssue:
    offset: int
    opcode: int | None
    reason: str


@dataclass(frozen=True)
class DecodeResult:
    audio_opcodes: list[DecodedAudioOpcode]
    issues: list[DecodeIssue]


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def remaining(self) -> int:
        return len(self.data) - self.pos

    def byte(self) -> int:
        if self.remaining() < 1:
            raise EOFError
        value = self.data[self.pos]
        self.pos += 1
        return value

    def word(self) -> int:
        if self.remaining() < 2:
            raise EOFError
        value = int.from_bytes(self.data[self.pos : self.pos + 2], "little")
        self.pos += 2
        return value

    def var_or_direct_byte(self, opcode: int, mask: int) -> tuple[int | None, str]:
        if opcode & mask:
            variable = self.word()
            return variable, "var"
        return self.byte(), "direct"

    def var_or_direct_word(self, opcode: int, mask: int) -> tuple[int | None, str]:
        value = self.word()
        if opcode & mask:
            return value, "var"
        return value, "direct"

    def result_pos(self) -> None:
        result = self.word()
        if result & 0x2000:
            self.word()

    def skip_varargs(self) -> None:
        while True:
            value = self.byte()
            if value == 0xFF:
                return
            if value & 0x80:
                self.word()
            else:
                self.byte()

    def skip_string(self) -> None:
        while True:
            value = self.byte()
            if value == 0:
                return
            if value == 0xFF:
                command = self.byte()
                if command == 0x0A:
                    self.word()

    def parse_string(self) -> None:
        while True:
            opcode = self.byte()
            if opcode == 0xFF:
                return
            base = opcode & 0x0F
            if base == 0:
                self.var_or_direct_word(opcode, PARAM_1)
                self.var_or_direct_word(opcode, PARAM_2)
            elif base == 1:
                self.var_or_direct_byte(opcode, PARAM_1)
            elif base == 2:
                self.var_or_direct_word(opcode, PARAM_1)
            elif base == 3:
                self.var_or_direct_word(opcode, PARAM_1)
                self.var_or_direct_word(opcode, PARAM_2)
            elif base in {4, 6, 7}:
                continue
            elif base == 8:
                self.var_or_direct_word(opcode, PARAM_1)
                self.var_or_direct_word(opcode, PARAM_2)
            elif base == 15:
                self.skip_string()
                return
            else:
                raise ValueError(f"unsupported print subopcode 0x{opcode:02x}")


def decode_audio_opcodes(data: bytes) -> DecodeResult:
    reader = _Reader(data)
    hits: list[DecodedAudioOpcode] = []
    issues: list[DecodeIssue] = []

    while reader.pos < len(data):
        offset = reader.pos
        try:
            opcode = reader.byte()
            if opcode in {0x00, 0xA0}:
                break
            _skip_opcode(reader, opcode, hits, offset)
        except EOFError:
            issues.append(DecodeIssue(offset=offset, opcode=data[offset] if offset < len(data) else None, reason="truncated operand"))
            break
        except ValueError as error:
            issues.append(DecodeIssue(offset=offset, opcode=data[offset], reason=str(error)))
            break

    return DecodeResult(audio_opcodes=hits, issues=issues)


def _skip_opcode(reader: _Reader, opcode: int, hits: list[DecodedAudioOpcode], offset: int) -> None:
    base = opcode & 0x7F

    if opcode == 0x80:
        return
    if opcode == 0x98:
        reader.byte()
        return
    if opcode == 0xCC:
        reader.byte()
        while reader.byte() != 0:
            continue
        return
    if opcode == 0xAE:
        subopcode = reader.byte()
        if (subopcode & 0x1F) == 1:
            reader.var_or_direct_byte(subopcode, PARAM_1)
        return
    if opcode == 0xD8:
        reader.parse_string()
        return

    if base == 0x02:
        value, kind = reader.var_or_direct_byte(opcode, PARAM_1)
        hits.append(DecodedAudioOpcode(offset=offset, opcode=opcode, name="startMusic", argument=value if kind == "direct" else None, argument_kind=kind))
        return
    if base == 0x1C:
        value, kind = reader.var_or_direct_byte(opcode, PARAM_1)
        hits.append(DecodedAudioOpcode(offset=offset, opcode=opcode, name="startSound", argument=value if kind == "direct" else None, argument_kind=kind))
        return

    if base in {0x03, 0x06, 0x0F, 0x10, 0x22, 0x23, 0x31, 0x3B, 0x43, 0x56, 0x63, 0x6C, 0x71, 0x7B}:
        reader.result_pos()
        reader.var_or_direct_byte(opcode, PARAM_1)
        return
    if base in {0x15, 0x34, 0x35, 0x55, 0x66, 0x74, 0x75}:
        reader.result_pos()
        reader.var_or_direct_word(opcode, PARAM_1)
        reader.var_or_direct_word(opcode, PARAM_2)
        return
    if base in {0x04, 0x08, 0x17, 0x1B, 0x38, 0x44, 0x48, 0x57, 0x78}:
        reader.var_or_direct_word(opcode, PARAM_1)
        reader.var_or_direct_word(opcode, PARAM_2)
        reader.word()
        return
    if base in {0x28, 0x68, 0x7C}:
        reader.var_or_direct_byte(opcode, PARAM_1)
        reader.word()
        return
    if base in {0x01, 0x21, 0x41, 0x61}:
        reader.var_or_direct_byte(opcode, PARAM_1)
        reader.var_or_direct_word(opcode, PARAM_2)
        reader.var_or_direct_word(opcode, PARAM_3)
        return
    if base in {0x05, 0x25, 0x65}:
        reader.var_or_direct_word(opcode, PARAM_1)
        reader.var_or_direct_word(opcode, PARAM_2)
        return
    if base in {0x09, 0x0D, 0x11, 0x2D, 0x36, 0x49, 0x4D, 0x51, 0x5E, 0x6D, 0x76, 0x7E}:
        reader.var_or_direct_byte(opcode, PARAM_1)
        reader.var_or_direct_byte(opcode, PARAM_2)
        return
    if base in {0x0A, 0x2A, 0x4A, 0x6A, 0x42}:
        reader.var_or_direct_byte(opcode, PARAM_1)
        reader.skip_varargs()
        return
    if base in {0x37, 0x77}:
        reader.var_or_direct_word(opcode, PARAM_1)
        reader.var_or_direct_byte(opcode, PARAM_2)
        reader.skip_varargs()
        return
    if base in {0x0B, 0x4B}:
        reader.result_pos()
        reader.var_or_direct_word(opcode, PARAM_1)
        reader.var_or_direct_word(opcode, PARAM_2)
        return
    if base == 0x0C:
        subopcode = reader.byte()
        if subopcode != 17:
            reader.var_or_direct_byte(subopcode, PARAM_1)
        subbase = subopcode & 0x3F
        if subbase == 20:
            reader.var_or_direct_word(subopcode, PARAM_2)
        elif subbase == 35:
            reader.var_or_direct_byte(subopcode, PARAM_2)
        elif subbase == 36:
            reader.var_or_direct_byte(subopcode, PARAM_2)
            reader.byte()
        elif subbase == 37:
            reader.var_or_direct_byte(subopcode, PARAM_2)
        return
    if base in {0x0E, 0x4E}:
        reader.var_or_direct_byte(opcode, PARAM_1)
        reader.var_or_direct_word(opcode, PARAM_2)
        return
    if base in {0x12, 0x32, 0x52, 0x60, 0x72}:
        reader.var_or_direct_byte(opcode, PARAM_1)
        return
    if base in {0x13, 0x53}:
        reader.var_or_direct_byte(opcode, PARAM_1)
        while True:
            subopcode = reader.byte()
            if subopcode == 0xFF:
                break
            subbase = subopcode & 0x1F
            if subbase in {0, 1, 3, 4, 6, 9, 11, 12, 14, 16, 19, 22, 23}:
                reader.var_or_direct_byte(subopcode, PARAM_1)
            elif subbase in {2, 5, 7, 17}:
                reader.var_or_direct_byte(subopcode, PARAM_1)
                reader.var_or_direct_byte(subopcode, PARAM_2)
            elif subbase in {8, 10, 13, 18, 20, 21}:
                continue
            else:
                raise ValueError(f"unsupported actorOps subopcode 0x{subopcode:02x}")
        return
    if base == 0x14:
        reader.var_or_direct_byte(opcode, PARAM_1)
        reader.parse_string()
        return
    if base in {0x1A, 0x3A, 0x5A, 0x5B}:
        reader.var_or_direct_word(opcode, PARAM_1)
        reader.var_or_direct_word(opcode, PARAM_2)
        return
    if base in {0x18, 0x46, 0x62, 0x6B, 0x6E}:
        reader.word()
        return
    if base in {0x1E, 0x3E}:
        reader.var_or_direct_byte(opcode, PARAM_1)
        reader.var_or_direct_word(opcode, PARAM_2)
        reader.var_or_direct_word(opcode, PARAM_3)
        return
    if base in {0x1F, 0x5F}:
        reader.var_or_direct_byte(opcode, PARAM_1)
        reader.var_or_direct_byte(opcode, PARAM_2)
        reader.word()
        return
    if base == 0x1D:
        reader.var_or_direct_word(opcode, PARAM_1)
        while True:
            subopcode = reader.byte()
            if subopcode == 0xFF:
                break
            reader.var_or_direct_word(subopcode, PARAM_1)
        reader.word()
        return
    if base in {0x20, 0xC0}:
        return
    if base == 0x2E:
        reader.byte()
        reader.byte()
        reader.byte()
        return
    if base in {0x24, 0x64}:
        reader.var_or_direct_word(opcode, PARAM_1)
        reader.var_or_direct_byte(opcode, PARAM_2)
        reader.var_or_direct_byte(opcode, PARAM_3)
        return
    if base == 0x26:
        reader.word()
        count = reader.byte()
        for _ in range(count):
            if opcode & PARAM_1:
                reader.word()
            else:
                reader.byte()
        return
    if base == 0x2B:
        reader.word()
        return
    if base == 0x30:
        subopcode = reader.byte()
        if (subopcode & 0x1F) in {1, 2, 3}:
            reader.var_or_direct_byte(subopcode, PARAM_1)
            reader.var_or_direct_byte(subopcode, PARAM_2)
        return
    if base == 0x3C:
        reader.var_or_direct_byte(opcode, PARAM_1)
        return
    if base in {0x3D, 0x7D}:
        reader.result_pos()
        reader.var_or_direct_byte(opcode, PARAM_1)
        reader.var_or_direct_byte(opcode, PARAM_2)
        return
    if base in {0x3F, 0x7F}:
        for mask in (PARAM_1, PARAM_2, PARAM_3):
            reader.var_or_direct_word(opcode, mask)
        reader.word()
        reader.byte()
        return
    if base == 0x40:
        reader.skip_varargs()
        return
    if base in {0x54, 0xD4}:
        reader.var_or_direct_word(opcode, PARAM_1)
        reader.skip_string()
        return
    if base == 0x5D:
        reader.var_or_direct_word(opcode, PARAM_1)
        while True:
            subopcode = reader.byte()
            if subopcode == 0xFF:
                break
            reader.var_or_direct_word(subopcode, PARAM_1)
        return
    if base == 0x58:
        reader.byte()
        reader.word()
        return
    if base == 0x70:
        reader.byte()
        reader.byte()
        reader.byte()
        return

    raise ValueError(f"unsupported opcode 0x{opcode:02x}")
