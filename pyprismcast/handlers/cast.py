"""
Handles
prismcast cast requests.
"""
from pathlib import Path

from pyprismcast import chromecast as cc
from pyprismcast.errors import ChromecastNotFoundError
from pyprismcast.servers import media
from pyprismcast.servers.utils import get_local_ip
from pyprismcast.transcode import video
from pyprismcast.movies import select_movie


def cast(args):
    """
    Connects to Chromecast, starts media server and control server.
    """
    ip = get_local_ip()
    file = args.path

    # TODO: arg to say if not formatted correctly, transcode it automatically
    if not video.is_compatible(file):
        print(f"File {file} is not compatible.")

    media_server = media.run_server(file.parent)

    # === Conection to Chromecast ===
    default_device = args.device
    chromecasts = cc.get_chromecasts()

    if not chromecasts:
        raise ChromecastNotFoundError("Chromecasts not found nearby")

    if default_device and default_device not in chromecasts:
        raise ChromecastNotFoundError(f"Chromecast {default_device} not found.")

    cast = cc.select_chromecast(
        chromecasts=chromecasts,
        default_device=default_device
    )

    cc.connect(cast)

    # === Connected to Chromecast ===

    # Create player for control server
    player = cc.ChromecastPlayer(cast)

    movie = select_movie(file.parent, default_movie=file.name)

