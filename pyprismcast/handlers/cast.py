"""
Handles `prismcast cast` requests.
"""
import asyncio
from threading import Event

from pyprismcast import chromecast as cc
from pyprismcast.errors import IncompatibleVideoError
from pyprismcast.servers import media, control
from pyprismcast.servers.utils import get_local_ip
from pyprismcast.transcode import video
from pyprismcast.movies import select_movie


def cast(args):
    """
    Connects to Chromecast,
    starts media server and control server,
    and plays the selected movie on the Chromecast device.
    """
    file = args.path
    default_device = args.device
    subtitles = args.subtitles
    MEDIA_PORT = args.media_port
    CONTROL_PORT = args.control_port
    HOST = args.host

    ip = get_local_ip()

    if not video.is_compatible(file):
        print(
            f"File {file} is not compatible. Use `prismcast transcode`"
            f" to transcode the video to a compatible format."
        )
        raise IncompatibleVideoError(f"File {file} is not compatible with Chromecast.")

    media_server = media.MediaServer(file.parent, port=MEDIA_PORT)  # file.parent = dir parent
    media_server.start()

    # === Connection to Chromecast ===
    chromecasts = cc.get_chromecasts()

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
    url = f"http://{ip}:{MEDIA_PORT}/{movie.relative_to(file.parent)}"
    print(f"Media server URL: {url}")

    # If subs, create URL for subs and enable subs in player
    sub_url = None
    if subtitles:
        sub_url = f"http://{ip}:8000/{subtitles.relative_to(file.parent)}"
        player.subtitles.enabled = True
        print(f"Subtitles URL: {sub_url}")

    player.play_media(
        url=url,
        content_type="video/mp4",
        subtitle_url=sub_url
    )
    player.block_until_active(timeout=15)

    if player.wait_for_media_session(timeout=20):
        if subtitles:
            player.enable_subtitles(track_id=1)
            player.apply_subtitle_style()

    player.play()

    print(f"Playing on Chromecast '{cast.cast_info.friendly_name}'")

    shutdown_event = Event()

    control_server = control.ControlServer(
        player,
        webdir=control.WEB_DIR,
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
