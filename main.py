#!/usr/bin/env python3

import argparse
import time
from pathlib import Path

import chromecast as cc

from servers import media
from servers import control
from servers.utils import get_local_ip

from movies import select_movie

from transcode import video
from transcode import subtitles

BASE_DIR = Path(__file__).resolve().parent
MOVIES_DIR = BASE_DIR / "movies"
WEB_DIR = BASE_DIR / "web"

MEDIA_PORT = 8000
CONTROL_PORT = 8001
HOST = "0.0.0.0"


def parse_args():
    parser = argparse.ArgumentParser(
        description=("Chromecast local movie player with web control.")
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="Sub-command to run. Use 'help <command>' for more information.",
    )

    # Sub-command: transcode
    parser_transcode = subparsers.add_parser(
        "transcode",
        help=(
            "Transcode movie/s to playable format "
            "(h264 video, aac audio, mp4 container)."
        )
    )
    parser_transcode.add_argument(
        "path",
        type=str,
        help="Path to movie file or directory containing movies.",
    )
    parser_transcode


def run():
    ip = get_local_ip()

    # converts everything in MOVIES_DIR to a playable format if needed.
    # WARNING: this may take long!
    print("Checking if all movies are playable...")
    video.ensure_library_playable(MOVIES_DIR)

    # === Media server (hosts movie/video files) ===
    media_server = media.run_server(MOVIES_DIR, port=MEDIA_PORT)

    # === Chromecast connection ===
    chromecasts = cc.get_chromecasts()
    cast = cc.select_chromecast(chromecasts)
    cc.connect(cast)

    # Create controller and set up event listener (check __init__)
    player = cc.ChromecastPlayer(cast)

    # === Select movie ===
    movie = select_movie(MOVIES_DIR)

    # NOTE: if you have problems, check this url in your browser to see if it
    # is a firewall/proxy error
    url = f"http://{ip}:8000/{movie.relative_to(MOVIES_DIR)}"
    print(f"URL to Chromecast: {url}")

    # === Play ===
    # NOTE: In future, media could be different! (audio, images, etc)
    player.play_media(
        url=url,
        content_type="video/mp4",
        subtitle_url=f"http://{ip}:8000/wh40k_secret_level.eng.vtt",
    )
    player.block_until_active(timeout=15)

    for _ in range(20):
        player.mc.update_status()
        if player.mc.status.media_session_id is not None:
            break
        time.sleep(0.5)

    player.mc.enable_subtitle(1)

    player.play()

    print("Reproducing...")
    print("Press Ctrl+C to stop the server and disconnect from Chromecast.")

    control_server = control.ControlServer(player, webdir=WEB_DIR)
    player.add_listener(control_server.on_player_status)

    print(f"Control UI: http://{ip}:{CONTROL_PORT}")

    try:
        control_server.run(host=HOST, port=CONTROL_PORT)

    except KeyboardInterrupt:
        print("Stopping...")

    finally:
        media_server.shutdown()
        cast.quit_app()
        cast.disconnect()

    print("Exiting...")


if __name__ == "__main__":
    run()
