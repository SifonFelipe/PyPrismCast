"""
Handles
prismcast cast requests.
"""
import asyncio
from threading import Event

from pyprismcast import chromecast as cc
from pyprismcast.errors import ChromecastNotFoundError, IncompatibleVideoError
from pyprismcast.servers import media, control
from pyprismcast.servers.utils import get_local_ip
from pyprismcast.transcode import video
from pyprismcast.movies import select_movie
from pyprismcast.servers.utils import CONTROL_PORT, WEB_DIR, HOST


def cast(args):
    """
    Connects to Chromecast, starts media server and control server.
    """
    ip = get_local_ip()
    file = args.path

    # TODO: arg to say if not formatted correctly, transcode it automatically
    if not video.is_compatible(file):
        print(f"File {file} is not compatible.")
        raise IncompatibleVideoError(f"File {file} is not compatible with Chromecast.")

    media_server = media.MediaServer(file.parent)  # file.parent = dir parent

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

    # URL for Media Server
    url = f"http://{ip}:8000/{movie.relative_to(file.parent)}"
    print(f"Media server URL: {url}")

    sub_url = None
    if args.subtitles:
        sub_url = f"http://{ip}:8000/{args.subtitles.relative_to(file.parent)}"
        print(f"Subtitles URL: {sub_url}")

    player.play_media(
        url=url,
        content_type="video/mp4",
        subtitle_url=sub_url
    )
    player.block_until_active(timeout=15)

    player.wait_for_subtitles(timeout=20)

    player.play()

    print(f"Playing on Chromecast '{cast.cast_info.friendly_name}'")

    shutdown_event = Event()

    control_server = control.ControlServer(
        player,
        webdir=WEB_DIR,
        shutdown_event=shutdown_event
    )

    player.add_listener(control_server.on_player_status)

    print(f"Control UI: http://{ip}:{CONTROL_PORT}")

    try:
        asyncio.run(
            control_server.run(
                host=HOST,
                port=CONTROL_PORT
            )
        )

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        print("[main] Shutting down servers and connections...")

        media_server.shutdown()

        try:
            player.stop()
        except Exception:
            pass

        try:
            cast.quit_app()
            cast.disconnect()
        except Exception:
            pass

    print("Exiting...")
