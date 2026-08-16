from threading import Event

from chromecast import get_chromecasts, select_chromecast, connect
from server import run_server, get_local_ip, MOVIES_DIR
from movies import select_movie
from transcode import ensure_library_playable


def run():
    ip = get_local_ip()

    # converts everything in MOVIES_DIR to a playable format if needed.
    # WARNING: this may take long!
    print("Checking if all movies are playable...")
    ensure_library_playable(MOVIES_DIR)

    server = run_server()

    chromecasts = get_chromecasts()
    cast = select_chromecast(chromecasts)
    connect(cast)

    media_controller = cast.media_controller

    # get movie to play
    movie = select_movie(MOVIES_DIR)

    # NOTE: if you have problems, check this url in your browser to see if it
    # is a firewall/proxy error
    url = f"http://{ip}:8000/{movie.relative_to(MOVIES_DIR)}"
    print(f"URL to Chromecast: {url}")

    class StatusPrinter:
        def new_media_status(self, status):
            print(
                f"[chromecast] player_state={status.player_state} "
                f"idle_reason={status.idle_reason} "
                f"content_id={status.content_id}"
            )

    media_controller.register_status_listener(StatusPrinter())

    media_controller.play_media(url, "video/mp4")

    try:
        media_controller.block_until_active(timeout=15)
    except Exception as exc:
        print(f"Chromecast didn´t confirm status: {exc}")

    print(f"Status of player: {media_controller.status.player_state}")
    idle_reason = media_controller.status.idle_reason
    if idle_reason:
        print(f"Idle reason: {idle_reason}")

    media_controller.play()

    print("Reproducing...")

    try:
        Event().wait()
    except KeyboardInterrupt:
        server.shutdown()

    cast.quit_app()
    cast.disconnect()

    print("Exiting...")


run()
