from pyprismcast.transcode import video, subtitles


def transcode(args):
    """
    Transcodes a movie to playable format (h264 video, aac audio, mp4 container).
    Also generates subtitles in vtt format if the movie contains some.
    """
    path = args.path

    if path.is_file():
        print(f"Transcoding file: {path}")
        video.ensure_playable(path)

    elif path.is_dir():
        print(f"Transcoding directory: {path}")
        video.ensure_library_playable(path)

