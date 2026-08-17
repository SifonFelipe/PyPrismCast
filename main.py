from threading import Event
from pathlib import Path

import chromecast as cc
from servers import media
from servers import control
from servers.utils import get_local_ip
from movies import select_movie
from transcode import ensure_library_playable

MOVIES_DIR = Path("movies")


def run():
    ip = get_local_ip()

    # converts everything in MOVIES_DIR to a playable format if needed.
    # WARNING: this may take long!
    print("Checking if all movies are playable...")
    ensure_library_playable(MOVIES_DIR)

    # HTTP server that serves movies
    media_server = media.run_server(MOVIES_DIR)

    # Find Chromecast device
    chromecasts = cc.get_chromecasts()
    cast = cc.select_chromecast(chromecasts)
    cc.connect(cast)

    # Create controller
    player = cc.ChromecastPlayer(cast)

    # Control server
    control_server = control.run_control_server(player)

    # select movie
    movie = select_movie(MOVIES_DIR)

    # NOTE: if you have problems, check this url in your browser to see if it
    # is a firewall/proxy error
    url = f"http://{ip}:8000/{movie.relative_to(MOVIES_DIR)}"
    print(f"URL to Chromecast: {url}")

    cc.set_listener(cast)

    # NOTE: In future, media could be different! (audio, images, etc)
    player.play_media(url, "video/mp4")
    player.block_until_active()

    print(f"Status of player: {player.get_status()}")

    player.play()

    print("Reproducing...")

    try:
        Event().wait()

    except KeyboardInterrupt:
        print("Stopping...")

    finally:
        media_server.shutdown()
        cast.quit_app()
        cast.disconnect()

    print("Exiting...")


if __name__ == "__main__":
    run()
