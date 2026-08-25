import argparse
from pathlib import Path


def parse_args():
    """
    Parse command-line arguments for the prismcast application.
    """

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
    parser_transcode.add_argument(
        "-s",
        "--subtitles",
        action="store_true",
        help="Transcode path subtitle/s to vtt format.",
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
    parser_cast.add_argument(
        "-mp",
        "--media-port",
        type=int,
        default=8000,
        help="Port for the media server (default: 8000)."
    )
    parser_cast.add_argument(
        "-hp",
        "--control-port",
        type=int,
        default=8001,
        help="Port for the control server (default: 8001)."
    )
    parser_cast.add_argument(
        "-ho",
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host for the control server (default: 0.0.0.0)."
    )

    return parser.parse_args()
