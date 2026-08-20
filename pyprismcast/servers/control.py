import asyncio
import json
from queue import Queue
from threading import Thread

from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart, jsonify, render_template, websocket

from pyprismcast.chromecast.player import ChromecastPlayer


class ControlServer:
    def __init__(self, player: ChromecastPlayer, webdir, shutdown_event):
        self.player = player
        self.shutdown_event = shutdown_event

        # pychromecast -> ControlServer
        self.status_queue = Queue()

        # WebSocket -> asyncio.Queue individual
        self.clients: dict[object, asyncio.Queue] = {}

        self.app = Quart(
            __name__,
            template_folder=webdir / "templates",
            static_folder=webdir / "static",
        )

        self._setup_routes()

        @self.app.before_serving
        async def startup():
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())

        @self.app.after_serving
        async def shutdown():
            self._broadcast_task.cancel()

            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass


    def on_player_status(self, status):
        """ Called from pychromecast's thread """
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
            ws = websocket._get_current_object()
            print(f"[control] New WebSocket connection: {id(websocket)}")

            queue = asyncio.Queue()
            self.clients[ws] = queue

            try:
                # Send the initial status to the client
                await ws.send(
                    json.dumps({
                        "type": "status",
                        **self.player.status
                    })
                )

                receiver = asyncio.create_task(self._receive_commands(ws))
                sender = asyncio.create_task(self._send_events(ws, queue))

                done, pending = await asyncio.wait(
                    [receiver, sender],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()
            except Exception as exc:
                print(f"[control] WebSocket connection error: {exc}")

            finally:
                self.clients.pop(ws, None)
                print(f"[control] WebSocket connection closed: {id(websocket)}")

    async def _receive_commands(self, ws):
        while True:
            raw_message = await ws.receive()
            print(f"[control] Received: {raw_message}")
            await self.handle_command(raw_message)

    async def _send_events(self, ws, queue):
        while True:
            message = await queue.get()
            await ws.send(json.dumps(message))

    async def _broadcast_loop(self):
        while True:
            status = await asyncio.to_thread(self.status_queue.get)
            message = {
                "type": "status",
                **status
            }

            for queue in list(self.clients.values()):
                await queue.put(message)

    async def handle_command(self, raw_message):
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
                self.shutdown_event.set()
            case "volume_up":
                increment = message.get("increment", 0.1)
                self.player.volume_up(increment)
            case "volume_down":
                decrement = message.get("decrement", 0.1)
                self.player.volume_down(decrement)
            case _:
                print(f"[control] Unknown command: {command}")

    async def run(self, host="0.0.0.0", port=8001):
        config = Config()

        config.bind = [f"{host}:{port}"]

        await serve(self.app, config=config, shutdown_trigger=self._shutdown_trigger)

    async def _shutdown_trigger(self):
        await asyncio.to_thread(self.shutdown_event.wait)
