from scummkit import mi1_script_decode


def test_decode_audio_opcodes_reports_direct_audio_calls() -> None:
    result = mi1_script_decode.decode_audio_opcodes(b"\x02\x19\x1c\x08\x00")

    assert result.issues == []
    assert [(item.name, item.argument, item.argument_kind, item.offset) for item in result.audio_opcodes] == [
        ("startMusic", 25, "direct", 0),
        ("startSound", 8, "direct", 2),
    ]


def test_decode_audio_opcodes_skips_operand_bytes() -> None:
    result = mi1_script_decode.decode_audio_opcodes(b"\x01\x02\x1c\x00\x00\x00\x00")

    assert result.audio_opcodes == []
    assert result.issues == []


def test_decode_audio_opcodes_skips_speech_escape_bytes_in_strings() -> None:
    result = mi1_script_decode.decode_audio_opcodes(b"\xd8\x0f\xff\x0a\x02\x1cWoof.\x00\xae\x02\x00")

    assert result.audio_opcodes == []
    assert result.issues == []


def test_decode_audio_opcodes_marks_variable_audio_argument() -> None:
    result = mi1_script_decode.decode_audio_opcodes(b"\x82\x34\x12\x00")

    assert result.issues == []
    assert len(result.audio_opcodes) == 1
    assert result.audio_opcodes[0].name == "startMusic"
    assert result.audio_opcodes[0].argument is None
    assert result.audio_opcodes[0].argument_kind == "var"


def test_decode_audio_opcodes_stops_on_unsupported_opcode() -> None:
    result = mi1_script_decode.decode_audio_opcodes(b"\x13\x02\x19")

    assert result.audio_opcodes == []
    assert result.issues[0].offset == 0
    assert result.issues[0].opcode == 0x13
