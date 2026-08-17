import asyncio
import json

from queue import Queue

from threading import Thread
from hypercorn.asyncio import serve
from hypercorn.config import Config

from quart import Quart, jsonify, render_template, websocket

from chromecast.player import ChromecastPlayer


class ControlServer:
    def __init__(self, player: ChromecastPlayer, webdir):
        self.player = player
        self.status_queue = Queue()

        self.app = Quart(
            __name__,
            template_folder=webdir / "templates",
            static_folder=webdir / "static",
        )

        self._setup_routes()

    def on_player_status(self, status):
        self.status_queue.put(status)

    def _setup_routes(self):
        @self.app.get("/")
        async def index():
            return await render_template("index.html")

        @self.app.get("/api/status")
        async def status():
            return jsonify(self.player.status)

        @self.app.websocket("/ws")
        async def websocket_handler():
            while True:
                message = await websocket.receive()
                await self.handle_command(message)

    async def handle_command(self, raw_message: str):
        message = json.loads(raw_message)
        command = message.get("type")

        match command:
            case "play":
                self.player.play()
            case "pause":
                self.player.pause()
            case "toggle":
                self.player.toggle()
            case "seek_relative":
                seconds = message.get("seconds", 0)
                self.player.seek_relative(seconds)
            case "seek":
                position = message.get("position", 0)
                self.player.seek(position)
            case "stop":
                self.player.stop()
            case "volume_up":
                increment = message.get("increment", 0.1)
                self.player.volume_up(increment)
            case "volume_down":
                decrement = message.get("decrement", 0.1)
                self.player.volume_down(decrement)

    def start(self, host="0.0.0.0", port=8001):
        thread = Thread(
            target=self._run,
            args=(host, port),
            daemon=True
        )

        thread.start()

        print(f"[control] Server started on port {port}")

        return thread

    def run(
        self,
        host: str = "0.0.0.0",
        port: int = 8001,
    ):
        self.app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
        )
        # asyncio.run(self._run_async(host, port))

    async def _run_async(self, host: str, port: int):
        self._shutdown_event = asyncio.Event()

        config = Config()
        config.bind = [f"{host}:{port}"]

        await serve(
            self.app,
            config,
            shutdown_trigger=self._shutdown_event.wait
        )

    def stop(self):
        if self._shutdown_event is not None:
            pass

