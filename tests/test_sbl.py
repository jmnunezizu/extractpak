from pathlib import Path
import wave

from scummkit import sbl


def test_wav_to_sbl_bytes(tmp_path: Path) -> None:
    wav = tmp_path / "tiny.wav"
    with wave.open(str(wav), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(1)
        f.setframerate(22050)
        f.writeframes(b"\x80\x81\x82\x83")

    blob = sbl.wav_to_sbl_bytes(wav)

    assert blob[:4] == b"SBL "
    assert b"AUhd" in blob
    assert b"AUdt" in blob
    assert blob.endswith(b"\x80\x81\x82\x83\x00")
