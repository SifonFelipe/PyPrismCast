import time
from dataclasses import dataclass, field

from pychromecast.controllers.media import MediaStatusListener


@dataclass
class SubtitleStyle:
    foreground_color: str = "#FFFFFFFF"
    background_color: str = "#00000000"
    edge_type: str = "OUTLINE"
    edge_color: str = "#000000FF"
    font_scale: float = 1.0
    font_family: str = "Roboto"
    font_style: str = "NORMAL"

    def to_cast(self):
        style = {
            "foregroundColor": self.foreground_color,
            "backgroundColor": self.background_color,
            "edgeType": self.edge_type,
            "edgeColor": self.edge_color,
            "fontScale": self.font_scale,
            "fontStyle": self.font_style,
        }

        if self.font_family:
            style["fontFamily"] = self.font_family

        return style


@dataclass
class SubtitleConfig:
    enabled: bool = True
    selected_track: int | None = None
    style: SubtitleStyle = field(default_factory=SubtitleStyle)


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

        self.subtitles = SubtitleConfig()

    # === Status / Events ===
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
            "subtitles_enabled": self.subtitles.enabled,
            "subtitles_selected_track": self.subtitles.selected_track,
            "subtitles_style": self.subtitles.style.to_cast(),
        }

        for listener in self._listeners:
            try:
                listener(data)
            except Exception as exc:
                print(f"[chromecast] Error notifying listener: {exc}")

    # === Media setup ===
    def play_media(self, url, content_type, subtitle_url=None):
        self.mc.play_media(
            url,
            content_type=content_type,
            subtitles=subtitle_url,
            subtitles_lang="en",
            subtitles_mime="text/vtt",
            current_time=0,
        )

    def block_until_active(self, timeout=15):
        try:
            self.mc.block_until_active(timeout=timeout)
        except Exception as exc:
            print(f"Chromecast didn´t confirm status: {exc}")

    def wait_for_media_session(self, timeout=20):
        for _ in range(timeout):
            self.mc.update_status()

            if self.mc.status.media_session_id is not None:
                return True

            time.sleep(1)

        return False

    def enable_subtitles(self, track_id=1):
        self.mc.enable_subtitle(track_id)

        self.subtitles.enabled = True
        self.subtitles.selected_track = track_id

    def disable_subtitles(self):
        track_id = self.subtitles.selected_track or 1
        self.mc.disable_subtitle(track_id)

        self.subtitles.enabled = False

    def apply_subtitle_style(self):
        self.mc._send_command(
            {
                "type": "EDIT_TRACKS_INFO",
                "textTrackStyle": self.subtitles.style.to_cast()
            },
            None
        )

    @property
    def status(self):
        status = self.mc.status

        return {
            "state": status.player_state,
            "current_time": status.current_time or 0,
            "duration": status.duration or 0,
            "content_id": status.content_id,
            "volume_level": self.cast.status.volume_level,
            "idle_reason": status.idle_reason,
            "subtitles_enabled": self.subtitles.enabled,
            "subtitles_selected_track": self.subtitles.selected_track,
            "subtitles_style": self.subtitles.style.to_cast(),
        }

    # === Control methods ===
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
        status = self.mc.status

        current_time = status.current_time or 0
        duration = status.duration

        position = current_time + seconds

        if duration is not None:
            position = min(position, duration)

        position = max(0, position)

        self.mc.seek(position)

    def seek(self, position):
        self.mc.seek(position)  # Seek to position's seconds

    def stop(self):
        self.mc.stop()

    def set_volume(self, volume):
        volume = max(0.0, min(volume, 1.0))
        self.cast.set_volume(volume)

    def volume_up(self, increment=0.1):
        current_volume = self.cast.status.volume_level
        new_volume = min(current_volume + increment, 1.0)
        self.cast.set_volume(new_volume)

    def volume_down(self, decrement=0.1):
        current_volume = self.cast.status.volume_level
        new_volume = max(current_volume - decrement, 0.0)
        self.cast.set_volume(new_volume)

    def update_subtitles(self, **style):
        for key, value in style.items():
            if hasattr(self.subtitles.style, key):
                setattr(self.subtitles.style, key, value)

        self.apply_subtitle_style()
