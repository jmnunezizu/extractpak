from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from . import monster
from .audio import count_files, encode_wav, probe_some, require_audio_tools
from .runner import BuildError, Runner, require_dir, require_file


@dataclass
class Mi1VoiceOptions:
    builder: Path
    speech_wav: Path
    sfx_wav: Path
    out: Path
    audio: str
    dry_run: bool = False
    verbose: bool = False


@dataclass
class Mi2VoiceOptions:
    builder: Path
    speech_wav: Path
    patch_wav: Path
    out: Path
    audio: str
    dry_run: bool = False
    verbose: bool = False


def final_ext(audio: str) -> str:
    return "wav" if audio == "raw" else audio


def plan_voice_steps(game: str, audio: str) -> list[str]:
    if game == "mi1":
        return [
            "Normalize Speech.xwb and SFXNew.xwb WAV files into samples-wav/.",
            "Copy _cdt_silence and create voice.bat special-case _cdt_*.wav files with SoX.",
            "Replace TRL_57_bridge_16_2.wav and GUY_20_main-beach_71_3.wav as voice.bat does.",
            f"Convert samples to {audio} files in final-{audio}/.",
            "Stop before sbl.bat and cdaudio.bat.",
        ]
    if game == "mi2":
        return [
            "Normalize Speech.xwb and Patch.xwb WAV files into samples-wav/.",
            "Create voice.bat special-case _cdt_*.wav files with SoX.",
            f"Convert samples to {audio} files in final-{audio}/.",
            "Stop before build_monster archive generation.",
        ]
    raise BuildError(f"unsupported voice game: {game}")


def _safe_prepare(runner: Runner, out: Path) -> None:
    runner.clean_dir(out)
    if not runner.dry_run:
        (out / "samples-wav").mkdir(parents=True, exist_ok=True)
        (out / "tmp").mkdir(parents=True, exist_ok=True)


def _sample(samples: Path, name: str) -> Path:
    return samples / name


def _normalize_wavs(runner: Runner, src_dir: Path, label: str, samples: Path) -> None:
    wavs = sorted(src_dir.glob("*.wav"))
    runner.log(f"  normalizing {len(wavs)} {label} WAV file(s)...")
    for wav in wavs:
        dst = samples / wav.name
        if runner.verbose:
            runner.log(f"normalise {label}/{wav.name} -> samples-wav/{wav.name}")
        try:
            runner.run(["sox", wav, "-D", dst])
        except BuildError:
            if not wav.exists():
                time.sleep(0.1)
            if wav.exists():
                runner.run(["sox", wav, "-D", dst])
            else:
                raise


def _trim(runner: Runner, samples: Path, src: str, dst: str, start: str, length: str) -> None:
    require_file(_sample(samples, src))
    if runner.verbose:
        runner.log(f"sox trim {src} {start} {length} -> {dst}")
    runner.run(["sox", _sample(samples, src), "-D", "-c", "1", "-t", "wav", "-V0", _sample(samples, dst), "trim", start, length])


def _gain(runner: Runner, samples: Path, src: str, dst: str, gain: str) -> None:
    require_file(_sample(samples, src))
    if runner.verbose:
        runner.log(f"sox gain {src} {gain} -> {dst}")
    runner.run(["sox", _sample(samples, src), "-D", "-c", "1", "-t", "wav", "-V0", _sample(samples, dst), "gain", gain])


def _compand(runner: Runner, samples: Path, src: str, dst: str, curve: str, gain: str) -> None:
    require_file(_sample(samples, src))
    if runner.verbose:
        runner.log(f"sox compand {src} -> {dst}")
    runner.run(["sox", _sample(samples, src), "-D", "-c", "1", "-t", "wav", "-V0", _sample(samples, dst), "compand", "0.0,0.5", curve, gain, "-99"])


def _mix_compand(runner: Runner, samples: Path, src1: str, src2: str, dst: str, curve: str, gain: str) -> None:
    require_file(_sample(samples, src1))
    require_file(_sample(samples, src2))
    if runner.verbose:
        runner.log(f"sox mix {src1} {src2} -> {dst}")
    runner.run(["sox", _sample(samples, src1), _sample(samples, src2), "-m", "-D", "-c", "1", "-t", "wav", "-V0", _sample(samples, dst), "compand", "0.0,0.5", curve, gain, "-99"])


def _copy_silence(runner: Runner, tools: Path, samples: Path) -> None:
    if runner.verbose:
        runner.log("copy _cdt_silence -> _cdt_silence.wav")
    if runner.dry_run:
        runner.log(f"[dry-run] cp {tools / '_cdt_silence'} {samples / '_cdt_silence.wav'}")
    else:
        shutil.copy2(tools / "_cdt_silence", samples / "_cdt_silence.wav")


def _replace(path: Path, source: Path) -> None:
    path.unlink(missing_ok=True)
    source.replace(path)


def _make_mi1_special_cases(runner: Runner, tools: Path, samples: Path, temp: Path) -> None:
    _copy_silence(runner, tools, samples)
    for src, dst, start, length in [
        ("STN_59_stans_89_1.wav", "_cdt_you_could.wav", "0.000", "3.375"),
        ("STN_59_stans_76_1.wav", "_cdt_10000.wav", "3.002", "0.962"),
        ("STN_59_stans_96_1.wav", "_cdt_9000.wav", "3.344", "1.009"),
        ("STN_59_stans_97_1.wav", "_cdt_8000.wav", "3.396", "0.695"),
        ("STN_59_stans_99_1.wav", "_cdt_7000.wav", "3.204", "0.812"),
        ("STN_59_stans_101_1.wav", "_cdt_6000.wav", "3.159", "0.813"),
        ("STN_59_stans_103_1.wav", "_cdt_5000.wav", "3.402", "0.765"),
        ("STN_59_stans_69_2.wav", "_cdt_4000.wav", "0.000", "0.919"),
        ("STN_59_stans_67_2.wav", "_cdt_3000.wav", "0.000", "1.395"),
        ("STN_59_stans_113_1.wav", "_cdt_900.wav", "4.180", "0.430"),
        ("STN_59_stans_103_1.wav", "_cdt_800.wav", "4.180", "0.430"),
        ("STN_59_stans_101_1.wav", "_cdt_700.wav", "3.972", "0.626"),
        ("STN_59_stans_99_1.wav", "_cdt_600.wav", "4.016", "0.578"),
        ("STN_59_stans_89_1.wav", "_cdt_500.wav", "4.318", "0.508"),
        ("STN_59_stans_112_1.wav", "_cdt_400.wav", "3.713", "0.640"),
        ("STN_59_stans_102_1.wav", "_cdt_300.wav", "3.860", "0.692"),
        ("STN_59_stans_100_1.wav", "_cdt_200.wav", "3.830", "0.691"),
        ("STN_59_stans_98_1.wav", "_cdt_100.wav", "3.721", "0.663"),
        ("STN_59_stans_97_1.wav", "_cdt_n50.wav", "4.593", "0.613"),
        ("STN_59_stans_90_1.wav", "_cdt_pieces.wav", "4.531", "0.705"),
        ("130_Monkey_Bride.wav", "_cdt_bride.wav", "5.382", "4.246"),
    ]:
        _trim(runner, samples, src, dst, start, length)

    _mix_compand(runner, samples, "SMK_43_trainers-house_16_22.wav", "50_sound_SBL_the-machine.wav", "_cdt_machine.wav", "-4.3,-4.3,-0,-4.3", "4")
    _gain(runner, samples, "Sheriff_UnknownFilename_03.wav", "_cdt_psssst.wav", "-15")
    _compand(runner, samples, "TRL_57_bridge_16_2.wav", "_cdt_eatya.wav", "-8.3,-8.3,-0,-8.3", "8")
    _gain(runner, samples, "GUY_20_main-beach_71_3.wav", "_cdt_ht.wav", "-4")
    _trim(runner, samples, "2_sound_SBL_door-open.wav", "_cdt_dooropen.wav", "0.005", "0.390")
    _trim(runner, samples, "3_sound_SBL_door-close.wav", "_cdt_doorclose.wav", "0.011", "0.222")
    runner.run(["sox", _sample(samples, "_cdt_dooropen.wav"), "-D", "-c", "1", "-t", "wav", "-V0", _sample(samples, "_cdt_dooropen.tmp.wav"), "gain", "-3"])
    runner.run(["sox", _sample(samples, "_cdt_doorclose.wav"), "-D", "-c", "1", "-t", "wav", "-V0", _sample(samples, "_cdt_doorclose.tmp.wav"), "gain", "-2"])
    if not runner.dry_run:
        _replace(_sample(samples, "_cdt_dooropen.wav"), _sample(samples, "_cdt_dooropen.tmp.wav"))
        _replace(_sample(samples, "_cdt_doorclose.wav"), _sample(samples, "_cdt_doorclose.tmp.wav"))
    _trim(runner, samples, "67_sound_SBL_soup-bubble.wav", "_cdt_bubble.wav", "0.013", "0.337")
    runner.run(["sox", _sample(samples, "_cdt_bubble.wav"), "-D", "-c", "1", "-t", "wav", "-V0", _sample(samples, "_cdt_bubble.tmp.wav"), "gain", "-6"])
    if not runner.dry_run:
        _replace(_sample(samples, "_cdt_bubble.wav"), _sample(samples, "_cdt_bubble.tmp.wav"))

    _mix_compand(runner, samples, "22_sound_SBL_whack_01.wav", "110_Guybrush_Punched.wav", "_cdt_guykick1.wav", "-4.3,-4.3,-0,-4.3", "4")
    _mix_compand(runner, samples, "22_sound_SBL_whack_01.wav", "StanTheSalesman_Grunt_03.wav", "_cdt_stankick.wav", "-4.3,-4.3,-0,-4.3", "4")
    _trim(runner, samples, "144_Fight_Stage_5_Shredder.wav", "_cdt_shredder.wav", "0.245", "5.121")
    for idx in range(1, 11):
        _mix_compand(runner, samples, f"FreddyFreak_Grunts_{idx:02d}.wav", "109_Head_Hit_01.wav", f"_cdt_hit{idx:02d}.wav", "-6.3,-6.3,-0,-6.3", "6")
    _mix_compand(runner, samples, "PHN_35_low-street_63_4.wav", "FRK_35_low-street_63_5.wav", "_cdt_jamrum.wav", "-4.3,-4.3,-0,-4.3", "4")
    require_file(_sample(samples, "FRK_35_low-street_63_3.wav"))
    require_file(_sample(samples, "PHN_35_low-street_63_2.wav"))
    if runner.verbose:
        runner.log("sox delay FRK_35_low-street_63_3.wav -> temp.wav")
    runner.run(["sox", _sample(samples, "FRK_35_low-street_63_3.wav"), "-t", "wav", "-V0", temp / "temp.wav", "delay", "0.25"])
    runner.run(["sox", temp / "temp.wav", _sample(samples, "PHN_35_low-street_63_2.wav"), "-m", "-D", "-c", "1", "-t", "wav", "-V0", _sample(samples, "_cdt_rumjam.wav"), "compand", "0.0,0.5", "-4.3,-4.3,-0,-4.3", "4", "-99"])
    if not runner.dry_run:
        _replace(_sample(samples, "TRL_57_bridge_16_2.wav"), _sample(samples, "_cdt_eatya.wav"))
        _replace(_sample(samples, "GUY_20_main-beach_71_3.wav"), _sample(samples, "_cdt_ht.wav"))
        if not runner.verbose:
            (temp / "temp.wav").unlink(missing_ok=True)


def _make_mi2_special_cases(runner: Runner, tools: Path, samples: Path, temp: Path) -> None:
    require_file(_sample(samples, "000003d5.wav"))
    require_file(_sample(samples, "vx112_DemBones_SE_nl_1.wav"))
    require_file(_sample(samples, "vx112_DemBones_SE_nl_2.wav"))
    if runner.verbose:
        runner.log("build _cdt_parlay.wav from 000003d5.wav")
    runner.run(["sox", "-r", "42777", _sample(samples, "000003d5.wav"), "-D", "-c", "1", "-t", "wav", "-V0", temp / "temp1.wav", "trim", "2.866", "1.230"])
    runner.run(["sox", temp / "temp1.wav", "-r", "48016", "-D", "-c", "1", "-t", "wav", "-V0", temp / "temp2.wav"])
    runner.run(["sox", _sample(samples, "000003d5.wav"), "-D", "-c", "1", "-t", "wav", "-V0", temp / "temp1.wav", "trim", "0.000", "2.553"])
    runner.run(["sox", temp / "temp1.wav", temp / "temp2.wav", _sample(samples, "_cdt_parlay.wav")])
    for src, dst, start, length in [
        ("vx112_DemBones_SE_nl_1.wav", "_cdt_arm_con1.wav", "71.881", "2.073"),
        ("vx112_DemBones_SE_nl_1.wav", "_cdt_hea_con1.wav", "10.943", "2.059"),
        ("vx112_DemBones_SE_nl_1.wav", "_cdt_hip_con1.wav", "31.281", "2.020"),
        ("vx112_DemBones_SE_nl_2.wav", "_cdt_leg_con1.wav", "31.257", "2.075"),
        ("vx112_DemBones_SE_nl_1.wav", "_cdt_rip_con1.wav", "79.304", "2.056"),
        ("vx112_DemBones_SE_nl_1.wav", "_cdt_arm_bone.wav", "33.536", "1.098"),
        ("vx112_DemBones_SE_nl_1.wav", "_cdt_hea_bone.wav", "74.208", "1.178"),
        ("vx112_DemBones_SE_nl_1.wav", "_cdt_hip_bone.wav", "20.673", "1.184"),
        ("vx112_DemBones_SE_nl_1.wav", "_cdt_leg_bone.wav", "53.883", "1.245"),
        ("vx112_DemBones_SE_nl_1.wav", "_cdt_rip_bone.wav", "40.999", "1.161"),
        ("vx112_DemBones_SE_nl_1.wav", "_cdt_arm_con2.wav", "34.994", "2.068"),
        ("vx112_DemBones_SE_nl_1.wav", "_cdt_hea_con2.wav", "75.610", "2.099"),
        ("vx112_DemBones_SE_nl_2.wav", "_cdt_hip_con2.wav", "35.005", "2.051"),
        ("vx112_DemBones_SE_nl_1.wav", "_cdt_leg_con2.wav", "55.252", "2.110"),
        ("vx112_DemBones_SE_nl_1.wav", "_cdt_rip_con2.wav", "14.655", "2.009"),
    ]:
        _trim(runner, samples, src, dst, start, length)
    _copy_silence(runner, tools, samples)
    if not runner.dry_run and not runner.verbose:
        (temp / "temp1.wav").unlink(missing_ok=True)
        (temp / "temp2.wav").unlink(missing_ok=True)


def _encode_samples(runner: Runner, samples: Path, final: Path, audio: str) -> None:
    if not runner.dry_run:
        final.mkdir(parents=True, exist_ok=True)
    wavs = sorted(samples.glob("*.wav"))
    runner.log(f"  encoding {len(wavs)} sample(s) as {audio}...")
    for wav in wavs:
        require_file(wav)
        if runner.verbose:
            runner.log(f"encode {audio} {wav.stem}")
        encode_wav(runner, wav, final / f"{wav.stem}.{final_ext(audio)}", audio)


def _monster_ref_names(table: Path) -> set[str]:
    return {name for _offset, name in monster.parse_table_or_raise(table)}


def _write_coverage(out: Path, refs: set[str], samples: set[str]) -> tuple[int, int]:
    missing = sorted(refs - samples)
    unreferenced = sorted(samples - refs)
    (out / "monster-refs.txt").write_text("\n".join(sorted(refs)) + "\n", encoding="utf-8")
    (out / "sample-names.txt").write_text("\n".join(sorted(samples)) + "\n", encoding="utf-8")
    (out / "missing-monster-samples.txt").write_text("\n".join(missing) + ("\n" if missing else ""), encoding="utf-8")
    (out / "unreferenced-samples.txt").write_text("\n".join(unreferenced) + ("\n" if unreferenced else ""), encoding="utf-8")
    return len(missing), len(unreferenced)


def process_mi1_voices(options: Mi1VoiceOptions) -> Path:
    runner = Runner(options.dry_run, options.verbose)
    builder = options.builder.expanduser()
    tools = builder / "tools"
    samples = options.out.expanduser() / "samples-wav"
    temp = options.out.expanduser() / "tmp"
    final = options.out.expanduser() / f"final-{options.audio}"
    require_dir(builder, "MI1 Ultimate Talkie builder directory")
    require_dir(tools, "MI1 builder tools directory")
    require_file(tools / "_cdt_silence", "MI1 voice helper sample")
    require_file(tools / "monster.tbl", "MI1 monster table")
    require_dir(options.speech_wav, "MI1 extracted speech WAV directory")
    require_dir(options.sfx_wav, "MI1 extracted SFX WAV directory")
    require_file(options.speech_wav / "STN_59_stans_89_1.wav", "MI1 Speech.xwb extracted sample")
    require_file(options.sfx_wav / "2_sound_SBL_door-open.wav", "MI1 SFXNew.xwb extracted sample")
    require_audio_tools(runner, options.audio)
    runner.log("MI1 voice processing")
    runner.log(f"speech wav: {options.speech_wav}")
    runner.log(f"sfx wav:    {options.sfx_wav}")
    runner.log(f"out:        {options.out}")
    runner.log(f"audio:      {options.audio}")
    if options.dry_run:
        runner.log("")
        runner.log("Planned voice steps:")
        for step in plan_voice_steps("mi1", options.audio):
            runner.log(f"- {step}")
        return final
    _safe_prepare(runner, options.out)
    _normalize_wavs(runner, options.sfx_wav, "sfx", samples)
    _normalize_wavs(runner, options.speech_wav, "speech", samples)
    normalized_count = count_files(samples, "*.wav")
    runner.log("  applying voice.bat special cases...")
    _make_mi1_special_cases(runner, tools, samples, temp)
    sample_count = count_files(samples, "*.wav")
    _encode_samples(runner, samples, final, options.audio)
    ext = final_ext(options.audio)
    processed_count = count_files(final, f"*.{ext}")
    refs = _monster_ref_names(tools / "monster.tbl")
    available = {p.stem for p in final.glob(f"*.{ext}")}
    missing_count, unreferenced_count = _write_coverage(options.out, refs, available)
    runner.log("")
    runner.log("Voice processing complete.")
    runner.log(f"Normalized WAV files: {normalized_count}")
    runner.log(f"WAV files after special cases: {sample_count}")
    runner.log(f"Processed {options.audio} files: {processed_count}")
    runner.log(f"Expected unique monster.tbl references: {len(refs)}")
    runner.log(f"Missing monster.tbl samples: {missing_count}")
    runner.log(f"Unreferenced processed samples: {unreferenced_count}")
    if missing_count:
        runner.log(f"warning: missing sample names written to {options.out / 'missing-monster-samples.txt'}")
    if unreferenced_count:
        runner.log(f"warning: unreferenced sample names written to {options.out / 'unreferenced-samples.txt'}")
    probe_some(runner, final)
    runner.log("Processed files are in:")
    runner.log(f"  {final}")
    return final


def process_mi2_voices(options: Mi2VoiceOptions) -> Path:
    runner = Runner(options.dry_run, options.verbose)
    builder = options.builder.expanduser()
    tools = builder / "tools"
    samples = options.out.expanduser() / "samples-wav"
    temp = options.out.expanduser() / "tmp"
    final = options.out.expanduser() / f"final-{options.audio}"
    require_dir(builder, "MI2 Ultimate Talkie builder directory")
    require_dir(tools, "MI2 builder tools directory")
    require_file(tools / "_cdt_silence", "MI2 voice helper sample")
    require_file(tools / "monster.tbl", "MI2 monster table")
    require_dir(options.speech_wav, "MI2 extracted speech WAV directory")
    require_dir(options.patch_wav, "MI2 extracted patch WAV directory")
    require_file(options.speech_wav / "00000000.wav", "MI2 Speech.xwb extracted sample")
    require_file(options.speech_wav / "000003d5.wav", "MI2 Speech.xwb extracted sample")
    require_file(options.patch_wav / "vx112_DemBones_SE_nl_1.wav", "MI2 Patch.xwb extracted sample")
    require_file(options.patch_wav / "vx112_DemBones_SE_nl_2.wav", "MI2 Patch.xwb extracted sample")
    require_audio_tools(runner, options.audio)
    runner.log("MI2 voice processing")
    runner.log(f"speech wav: {options.speech_wav}")
    runner.log(f"patch wav:  {options.patch_wav}")
    runner.log(f"out:        {options.out}")
    runner.log(f"audio:      {options.audio}")
    if options.dry_run:
        runner.log("")
        runner.log("Planned voice steps:")
        for step in plan_voice_steps("mi2", options.audio):
            runner.log(f"- {step}")
        return final
    _safe_prepare(runner, options.out)
    _normalize_wavs(runner, options.speech_wav, "speech", samples)
    _normalize_wavs(runner, options.patch_wav, "patch", samples)
    normalized_count = count_files(samples, "*.wav")
    runner.log("  applying voice.bat special cases...")
    _make_mi2_special_cases(runner, tools, samples, temp)
    sample_count = count_files(samples, "*.wav")
    _encode_samples(runner, samples, final, options.audio)
    ext = final_ext(options.audio)
    processed_count = count_files(final, f"*.{ext}")
    expected_count = len(_monster_ref_names(tools / "monster.tbl"))
    runner.log("")
    runner.log("Voice processing complete.")
    runner.log(f"Normalized WAV files: {normalized_count}")
    runner.log(f"WAV files after special cases: {sample_count}")
    runner.log(f"Processed {options.audio} files: {processed_count}")
    runner.log(f"Expected unique monster.tbl references: {expected_count}")
    if processed_count != expected_count:
        runner.log("warning: processed file count differs from monster.tbl references; build_monster may intentionally ignore unused samples.")
    probe_some(runner, final)
    runner.log("Processed files are in:")
    runner.log(f"  {final}")
    return final
