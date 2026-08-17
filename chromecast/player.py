class ChromecastPlayer:
    def __init__(self, cast):
        self.cast = cast
        self.mc = cast.media_controller

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
            self.cast.media_controller.pause()
        else:
            self.cast.media_controller.play()

    def seek_relative(self, seconds):
        status = self.cast.media_controller.status
        position = status.current_time + seconds

        position = max(0, min(position, status.duration))

        self.cast.media_controller.seek(position)

    def seek(self, position):
        self.mc.seek(position)  # Seek to position's seconds

    def stop(self):
        self.mc.stop()

    def set_volume(self, volume):
        self.cast.set_volume(volume)

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
        return self.mc.status
