from collections.abc import Callable
from typing import Any
from pychromecast.controllers.media import MediaStatusListener


class ChromecastStatusListener(MediaStatusListener):
    def __init__(self, player):
        self.player = player

    def new_media_status(self, status):
        print(
            f"[chromecast] player_state={status.player_state} "
            f"idle_reason={status.idle_reason} "
            f"content_id={status.content_id} "
            f"time={status.current_time}"
        )

        # Every change on chromecast status is notified to the player
        self.player._notify(status)

    def load_media_failed(self, queue_item_id: int, error_code: int):
        print(
            f"[chromecast] ERROR load_media_failed: "
            f"queue_item_id={queue_item_id} "
            f"error_code={error_code}"
        )


class ChromecastPlayer:
    def __init__(self, cast):
        self.cast = cast
        self.mc = cast.media_controller

        self._listeners = []

        # Set listener to receive status updates from the Chromecast device
        self._chromecast_listener = ChromecastStatusListener(self)
        self.mc.register_status_listener(self._chromecast_listener)

    def add_listener(self, callback):
        self._listeners.append(callback)

    def _notify(self, status):
        data = {
            "type": "status",
            "state": status.player_state,
            "current_time": status.current_time,
            "duration": status.duration,
            "content_id": status.content_id,
            "volume_level": status.volume_level,
            "idle_reason": status.idle_reason,
        }

        for listener in self._listeners:
            listener(data)

    def play_media(self, url, content_type):
        self.mc.play_media(url, content_type)

    def block_until_active(self, timeout=15):
        try:
            self.mc.block_until_active(timeout=timeout)
        except Exception as exc:
            print(f"Chromecast didn´t confirm status: {exc}")

    def get_status(self):
        status = self.cast.media_controller.status
        return {
            "player_state": status.player_state,
            "current_time": status.current_time,
            "duration": status.duration,
            "volume_level": self.cast.status.volume_level,
        }

    def play(self):
        self.mc.play()

    def pause(self):
        self.mc.pause()

    def toggle(self):
        status = self.cast.media_controller.status
        if status.player_state == "PLAYING":
            self.mc.pause()
        else:
            self.mc.play()

    def seek_relative(self, seconds):
        status = self.cast.media_controller.status
        position = status.current_time + seconds

        position = max(0, min(position, status.duration))

        self.mc.seek(position)

    def seek(self, position):
        self.mc.seek(position)  # Seek to position's seconds

    def stop(self):
        self.mc.stop()

    def set_volume(self, volume):
        self.cast.set_volume(min(1.0, volume))

    def volume_up(self, increment=0.1):
        current_volume = self.cast.status.volume_level
        new_volume = min(current_volume + increment, 1.0)
        self.cast.set_volume(new_volume)

    def volume_down(self, decrement=0.1):
        current_volume = self.cast.status.volume_level
        new_volume = max(current_volume - decrement, 0.0)
        self.cast.set_volume(new_volume)

    @property
    def status(self):
        status = self.mc.status

        return {
            "state": status.player_state,
            "current_time": status.current_time,
            "duration": status.duration,
            "content_id": status.content_id,
            "volume_level": status.volume_level,
        }
