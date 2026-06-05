from __future__ import annotations

import argparse
from pathlib import Path

from .. import monster
from .. import speech_manifest
from ..runner import BuildError


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("speech-manifest", help="generate and compare local speech manifests")
    games = parser.add_subparsers(dest="game", required=True)

    mi1 = games.add_parser("mi1", help="generate an MI1 manifest from Special Edition speech.info")
    mi1.add_argument("--speech-info", type=Path, required=True, help="MI1 Special Edition audio/speech.info")
    mi1.add_argument("--out", type=Path, required=True, help="JSON manifest output path")
    mi1.add_argument("--table-out", type=Path, help="optional generated monster.tbl-compatible output path")
    mi1.add_argument("--compare-table", type=Path, help="optional builder tools/monster.tbl to compare against")
    mi1.add_argument("--sfxnew", type=Path, help="optional MI1 Special Edition audio/SFXNew.xwb for diff classification")
    mi1.add_argument("--classify-out", type=Path, help="optional JSON output path for classified diff results")
    mi1.add_argument(
        "--coverage-mode",
        choices=["speech-info", "builder"],
        default="speech-info",
        help="manifest sample coverage to write; builder mode matches compare-table sample names",
    )
    mi1.set_defaults(func=run_mi1)


def run_mi1(args: argparse.Namespace) -> None:
    speech_info = args.speech_info.expanduser()
    out = args.out.expanduser()
    table_out = args.table_out.expanduser() if args.table_out is not None else None
    compare_table = args.compare_table.expanduser() if args.compare_table is not None else None
    sfxnew = args.sfxnew.expanduser() if args.sfxnew is not None else None
    classify_out = args.classify_out.expanduser() if args.classify_out is not None else None

    try:
        records = speech_manifest.parse_mi1_speech_info(speech_info)
        base_entries = speech_manifest.build_mi1_manifest(records)
        entries = base_entries
        if args.coverage_mode == "builder":
            if compare_table is None:
                raise speech_manifest.SpeechManifestError("--coverage-mode builder requires --compare-table")
            entries = speech_manifest.build_builder_coverage_manifest(base_entries, compare_table, sfxnew=sfxnew)
        speech_manifest.write_manifest(
            out,
            speech_manifest.manifest_payload("mi1", records, entries, coverage_mode=args.coverage_mode),
        )
        if table_out is not None:
            speech_manifest.write_monster_table(table_out, entries)
        print("MI1 speech manifest generated:")
        print(f"  coverage mode:  {args.coverage_mode}")
        print(f"  records:        {len(records)}")
        print(f"  unique samples: {len(entries)}")
        print(f"  manifest:       {out}")
        if table_out is not None:
            print(f"  table:          {table_out}")
        if compare_table is not None:
            comparison = speech_manifest.compare_with_builder(base_entries, compare_table)
            print("")
            print(speech_manifest.format_comparison(comparison, title="MI1 speech.info comparison"))
            if sfxnew is not None or classify_out is not None:
                classification = speech_manifest.classify_comparison(base_entries, compare_table, sfxnew=sfxnew)
                if classify_out is not None:
                    speech_manifest.write_classification(classify_out, classification)
                print("")
                print(speech_manifest.format_classification(classification))
                if classify_out is not None:
                    print(f"classification: {classify_out}")
            if args.coverage_mode != "speech-info":
                final_comparison = speech_manifest.compare_with_builder(entries, compare_table)
                print("")
                print(speech_manifest.format_comparison(final_comparison, title="MI1 written manifest comparison"))
    except (OSError, speech_manifest.SpeechManifestError, monster.MonsterError, speech_manifest.xwb.XwbError) as error:
        raise BuildError(str(error)) from error
