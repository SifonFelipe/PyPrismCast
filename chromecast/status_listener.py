from pychromecast import Chromecast
from pychromecast.controllers.media import MediaStatusListener


class StatusPrinter(MediaStatusListener):
    def new_media_status(self, status):
        print(
            f"[chromecast] player_state={status.player_state} "
            f"idle_reason={status.idle_reason} "
            f"content_id={status.content_id} "
            f"time={status.current_time}"
        )

    def load_media_failed(self, queue_item_id: int, error_code: int):
        print(
            f"[chromecast] ERROR load_media_failed: queue_item_id={queue_item_id} "
            f"error_code={error_code}"
        )


def set_listener(cast: Chromecast):
    media_controller = cast.media_controller
    media_controller.register_status_listener(StatusPrinter())
