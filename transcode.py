import functools
import json
import subprocess
import sys
from pathlib import Path

# Codecs that the Default Media Receiver of Chromecast can play natively.
COMPATIBLE_VIDEO_CODECS = {"h264"}
COMPATIBLE_AUDIO_CODECS = {"aac"}

# Common video file extensions to avoid processing stray images or text files
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm", ".m4v"}


def probe_video(path: Path) -> tuple[str, str, int, int]:
    """Returns (video_codec, pix_fmt, width, height) of the first video stream."""
    # NOTE: ffprobe's csv output does NOT preserve the field order given
    # in -show_entries (it uses its own internal order), so this parses
    # JSON and reads fields by name instead of by position.
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,pix_fmt,width,height",
        "-of", "json",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    streams = json.loads(result.stdout or "{}").get("streams", [])
    if not streams:
        return "", "", 0, 0

    stream = streams[0]
    return (
        stream.get("codec_name", ""),
        stream.get("pix_fmt", ""),
        int(stream.get("width", 0)),
        int(stream.get("height", 0)),
    )


def probe_audio(path: Path) -> tuple[str, int]:
    """Returns (audio_codec, channel_count) of the first audio stream."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name,channels",
        "-of", "json",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    streams = json.loads(result.stdout or "{}").get("streams", [])
    if not streams:
        return "", 0

    stream = streams[0]
    return stream.get("codec_name", ""), int(stream.get("channels", 0))


# If any other pix_fmt is detected, the video will be re-encoded to yuv420p.
COMPATIBLE_PIX_FMTS = {"yuv420p"}

# If more channels (5.1, 7.1) are detected, the audio will be downmixed to stereo
MAX_COMPATIBLE_CHANNELS = 2

# Regular (non-Ultra) Chromecasts top out at 1080p. Anything taller than
# this gets scaled down, which also makes encoding roughly 4x faster for
# 4K sources since there are far fewer pixels to process.
MAX_COMPATIBLE_HEIGHT = 1080


def is_compatible(path: Path) -> bool:
    """True if file is MP4 + H.264 8-bit + AAC stereo/mono, at <=1080p."""
    if path.suffix.lower() != ".mp4":
        return False

    video_codec, pix_fmt, width, height = probe_video(path)
    audio_codec, channels = probe_audio(path)

    return (
        video_codec in COMPATIBLE_VIDEO_CODECS
        and pix_fmt in COMPATIBLE_PIX_FMTS
        and height <= MAX_COMPATIBLE_HEIGHT
        and audio_codec in COMPATIBLE_AUDIO_CODECS
        and 0 < channels <= MAX_COMPATIBLE_CHANNELS
    )


def _temp_output_path(path: Path) -> Path:
    """
    Path used while re-encoding. ffmpeg can't read and write the same
    file at once, so conversion always goes through this temp file first;
    the original is only replaced once the whole conversion succeeds, so
    a crash or Ctrl+C mid-encode never leaves a half-written file behind.
    """
    return path.with_name(f".{path.stem}.converting.mp4")


# Video encoders by hardware, in order of preference.
HARDWARE_VIDEO_ENCODERS = [
    # Nvidia (Linux/Windows)
    ("h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]),
    # Apple Silicon / Intel Mac
    ("h264_videotoolbox", ["-c:v", "h264_videotoolbox", "-b:v", "6M"]),
    # Intel QuickSync (Linux/Windows)
    ("h264_qsv", ["-c:v", "h264_qsv", "-preset", "fast", "-global_quality", "23"]),
]

# libx264 preset if no hardware encoder is available
LIBX264_PRESET = "veryfast"
LIBX264_FALLBACK_ARGS = ["-c:v", "libx264", "-preset", LIBX264_PRESET, "-crf", "21"]

_working_video_encoder: list[str] | None = None


@functools.lru_cache(maxsize=1)
def _available_encoders() -> str:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"],
        capture_output=True, text=True,
    )
    return result.stdout


def _video_encoder_candidates() -> list[list[str]]:
    if _working_video_encoder is not None:
        return [_working_video_encoder]

    encoders = _available_encoders()
    candidates = [args for name, args in HARDWARE_VIDEO_ENCODERS if name in encoders]
    candidates.append(LIBX264_FALLBACK_ARGS)
    return candidates


def _test_encoder(path: Path, video_args: list[str]) -> bool:
    """Runs a lightning-fast 1-second test to see if the hardware encoder works."""
    test_cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-t", "1",  # Only process 1 second of video
        "-i", str(path),
        *video_args,
        "-f", "null", "-"  # Discard output instantly without writing a file
    ]
    try:
        subprocess.run(test_cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False


def ensure_playable(path: Path) -> Path:
    """
    Makes sure `path` is playable by Chromecast, converting it *in place*
    if it isn't (no separate cache folder: the original file itself ends
    up being the compatible MP4, possibly under a new .mp4 extension if
    the container changed).

    Returns the (possibly renamed) path to the now-playable file.
    """
    if is_compatible(path):
        return path

    print(f"\nProcessing: '{path.name}'")

    video_codec, pix_fmt, width, height = probe_video(path)
    audio_codec, channels = probe_audio(path)

    # Check if there is even a video stream present
    if not video_codec:
        print(f"Skipping '{path.name}': No video stream found.")
        return path

    needs_video_encode = not (
        video_codec in COMPATIBLE_VIDEO_CODECS
        and pix_fmt in COMPATIBLE_PIX_FMTS
        and height <= MAX_COMPATIBLE_HEIGHT
    )

    if audio_codec in COMPATIBLE_AUDIO_CODECS and 0 < channels <= MAX_COMPATIBLE_CHANNELS:
        audio_args = ["-c:a", "copy"]
    else:
        audio_args = ["-c:a", "aac", "-ac", "2", "-b:a", "192k"]

    temp_output = _temp_output_path(path)

    def build_cmd(video_args: list[str]) -> list[str]:
        return [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "info", "-stats",
            "-i", str(path),
            *video_args,
            *audio_args,
            "-movflags", "+faststart",  # Allows streaming to start before full download
            str(temp_output),
        ]

    # Filter chain shared by every encoder: force 8-bit yuv420p (fixes
    # "High 10" HEVC 10-bit sources that Chromecast can't decode), and
    # scale down anything taller than 1080p.
    vf_filters = ["format=yuv420p"]
    if height > MAX_COMPATIBLE_HEIGHT:
        vf_filters.insert(0, f"scale=-2:{MAX_COMPATIBLE_HEIGHT}")
        print(f" -> Downscaling {width}x{height} to 1080p (much faster to encode)")
    vf_arg = ["-vf", ",".join(vf_filters)]

    global _working_video_encoder

    try:
        if not needs_video_encode:
            print(" -> Fast stream copying video track...")
            subprocess.run(build_cmd(["-c:v", "copy"]), check=True)
        else:
            candidates = _video_encoder_candidates()
            chosen_encoder = None

            for base_args in candidates:
                video_args = [*base_args, *vf_arg]

                # If it's the fallback or already known working encoder, skip the test trial
                if base_args == _working_video_encoder or base_args == LIBX264_FALLBACK_ARGS:
                    chosen_encoder = video_args
                    break

                print(f" -> Testing encoder capability: {base_args[1]}...")
                if _test_encoder(path, video_args):
                    _working_video_encoder = base_args
                    chosen_encoder = video_args
                    print(f"   Success! Selected hardware encoder: {base_args[1]}")
                    break
                else:
                    print(f"   Failed initial test for {base_args[1]}. Trying next...")

            if not chosen_encoder:
                raise RuntimeError(f"No video encoder worked for '{path.name}'")

            # Execute full conversion with stats progress bar visible to user
            print(" -> Re-encoding video stream...")
            subprocess.run(build_cmd(chosen_encoder), check=True)

        # Conversion succeeded: swap the original for the converted file.
        # If the extension changed (e.g. .mkv -> .mp4), the old file is
        # removed so there isn't a stale duplicate sitting next to it.
        target = path if path.suffix.lower() == ".mp4" else path.with_suffix(".mp4")
        if path != target and path.exists():
            path.unlink()
        temp_output.replace(target)

    except BaseException:
        # Conversion failed or was interrupted: clean up the temp file
        # and leave the original untouched.
        temp_output.unlink(missing_ok=True)
        raise

    print(f"Finished: {target.name}")
    return target


def ensure_library_playable(movies_dir: Path) -> None:
    # Explicitly filter out leftover temp files and check for video extensions
    movies = [
        p for p in movies_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in VIDEO_EXTENSIONS
        and not p.name.startswith(".")
    ]

    if not movies:
        print(f"No compatible video files found in '{movies_dir}'.")
        return

    print(f"Found {len(movies)} videos to review.")
    for movie in movies:
        try:
            ensure_playable(movie)
        except Exception as e:
            print(f"Error processing {movie.name}: {e}")

    print(f"\nLibrary sweep complete: {len(movies)} videos reviewed.")


if __name__ == "__main__":
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("movies")
    ensure_library_playable(directory)
