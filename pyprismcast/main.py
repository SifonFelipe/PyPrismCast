#!/usr/bin/env python3

import argparse
from pathlib import Path

from pyprismcast import handlers

BASE_DIR = Path(__file__).resolve().parent
MOVIES_DIR = BASE_DIR / "movies"
WEB_DIR = BASE_DIR / "web"

MEDIA_PORT = 8000
CONTROL_PORT = 8001
HOST = "0.0.0.0"


def parse_args():
    parser = argparse.ArgumentParser(
        prog="prismcast",
        description="Chromecast local movie player with web control.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="Command to run.",
    )

    # --- Sub-command: transcode ---
    parser_transcode = subparsers.add_parser(
        "transcode",
        help=(
            "Transcode movie/s to playable format (h264 video, aac audio, mp4 container). "
            "Also generates subtitles in vtt format if the movie contains some. "
            "This command also supports subtitles!"
        ),
    )
    parser_transcode.add_argument(
        "path",
        type=lambda p: Path(p).resolve(),
        help="Path to movie file or directory containing movies/subs.",
    )
    parser_transcode.add_argument(
        "-R",
        "--recursive",
        action="store_true",
        help="Recursively transcode movies in subdirectories.",
    )

    # --- Sub-command: cast ---
    parser_cast = subparsers.add_parser(
        "cast",
        help="Cast a movie to Chromecast and control it via web interface.",
    )
    parser_cast.add_argument(
        "path",
        type=lambda p: Path(p).resolve(),
        help="Path to movie file or directory containing movies.",
    )
    parser_cast.add_argument(
        "-s",
        "--subtitles",
        type=lambda p: Path(p).resolve(),
        help="Path to subtitle file (vtt format).",
    )
    parser_cast.add_argument(
        "-d",
        "--device",
        type=str,
        help="Name of the Chromecast device to cast to.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    command = args.command

    if command == "cast":
        handlers.cast(args)
    elif command == "transcode":
        handlers.transcode(args)
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
