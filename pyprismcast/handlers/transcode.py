from pyprismcast.transcode import video, subtitles
from pyprismcast.errors import SubtitleConversionError


def transcode(args):
    """
    Transcodes a movie to playable format (h264 video, aac audio, mp4 container).
    Also generates subtitles in vtt format if the movie contains some.
    """
    path = args.path

    if args.subtitles:
        if path.is_file():
            if path.suffix.lower() == ".srt":
                print(f"Transcoding subtitles for file: {path}")
                subtitles.convert_srt_to_vtt(
                    srt_path=path,
                    vtt_path=path.with_suffix(".vtt")
                )
                print(" -> Subtitle conversion complete.")

            else:
                raise SubtitleConversionError(
                    f"Unsupported subtitle file format: {path.suffix}"
                )

        elif path.is_dir():
            print(f"Transcoding subtitles for directory: {path}")
            subtitles.ensure_subtitles_playable(
                path,
                recursive=args.recursive
            )

        return

    if path.is_file():
        print(f"Transcoding file: {path}")
        video.ensure_playable(path)

    elif path.is_dir():
        print(f"Transcoding directory: {path}")
        video.ensure_library_playable(path, recursive=args.recursive)
