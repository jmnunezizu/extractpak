from pathlib import Path

from scummkit import mi1_sbl


def test_native_mi1_sbl_commands_are_complete() -> None:
    commands = mi1_sbl.native_sbl_commands()

    assert len(commands) == 71
    assert commands[0].source == "_cdt_bubble.wav"
    assert commands[0].room_id == 41
    assert commands[0].sound_id == 67
    assert commands[-1].source == "100_Ghost_Die.wav"
    assert commands[-1].room_id == 59
    assert commands[-1].sound_id == 174
    assert [command.index for command in commands] == list(range(1, 72))


def test_native_mi1_sbl_commands_match_local_builder_when_available() -> None:
    sbl_bat = Path("/Users/jmnunezizu/Downloads/MI1_Ultimate_Talkie_Edition_Builder/tools/sbl.bat")
    if not sbl_bat.exists():
        return

    assert mi1_sbl.compare_sbl_commands(mi1_sbl.native_sbl_commands(), mi1_sbl.parse_sbl_bat(sbl_bat)) == []
