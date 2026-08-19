"""
Format .srt subtitles to .vtt subtitles
because ChromeCast only supports .vtt subtitles
"""
import subprocess
import json
from pathlib import Path

TEXT_SUBTITLE_CODECS = {"srt", "ass", "webvtt", "subrip", "mov_text"}


def convert_srt_to_vtt(srt_path, vtt_path):
    with open(srt_path, encoding='utf-8-sig') as f:  # read
        text = f.read()

    vtt_content = "WEBVTT\n\n" + text.replace(',', '.')

    with open(vtt_path, 'w', encoding='utf-8') as f:
        f.write(vtt_content)


def probe_subtitles(path: Path) -> list[dict]:
    """Returns information about subtitle streams."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "s",
        "-show_entries", "stream=index,codec_name:stream_tags=language,title",
        "-of", "json",
        str(path),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout or "{}")
    streams = data.get("streams", [])

    subtitles = []

    for stream in streams:
        tags = stream.get("tags", {})

        subtitles.append({
            "index": stream.get("index"),
            "codec": stream.get("codec_name", ""),
            "language": tags.get("language"),
            "title": tags.get("title"),
        })

    return subtitles


def extract_subtitles(path: Path) -> list[Path]:
    """Extract all text subtitle streams as WebVTT."""

    subtitles = probe_subtitles(path)

    if not subtitles:
        return []

    extracted = []

    for subtitle_number, subtitle in enumerate(subtitles):
        codec = subtitle.get("codec", "")

        if not codec:
            print(
                f" -> Skipping subtitle {subtitle_number}: "
                "could not determine codec"
            )
            continue

        if codec not in TEXT_SUBTITLE_CODECS:
            print(
                f" -> Skipping subtitle {subtitle_number}: "
                f"unsupported codec '{codec}'"
            )
            continue

        language = subtitle.get("language") or f"track{subtitle_number}"

        language = "".join(
            c for c in language
            if c.isalnum() or c in "-_"
        )

        output = path.with_name(
            f"{path.stem}.{language}.vtt"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(path),
            "-map", f"0:s:{subtitle_number}",
            "-c:s", "webvtt",
            str(output),
        ]

        try:
            subprocess.run(cmd, check=True)
            extracted.append(output)

            print(f" -> Extracted subtitle: {output.name}")

        except subprocess.CalledProcessError as e:
            print(
                f" -> Failed to extract subtitle "
                f"{subtitle_number}: {e}"
            )

    return extracted
