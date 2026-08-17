from threading import Thread

from flask import Flask, jsonify, request

from chromecast.player import ChromecastPlayer


def create_control_server(player: ChromecastPlayer):
    app = Flask(__name__)

    @app.post("/player/play")
    def play():
        player.play()
        return jsonify(ok=True)

    @app.post("/player/pause")
    def pause():
        player.pause()
        return jsonify(ok=True)

    @app.post("/player/stop")
    def stop():
        player.stop()
        return jsonify(ok=True)

    @app.post("/player/seek")
    def seek():
        data = request.get_json()

        position = float(data["position"])

        player.seek(position)

        return jsonify(
            ok=True,
            position=position,
        )

    @app.post("/player/seek-relative")
    def seek_relative():
        data = request.get_json()

        seconds = float(data["seconds"])

        player.seek_relative(seconds)

        return jsonify(
            ok=True,
            seconds=seconds,
        )

    return app


def run_control_server(
    player: ChromecastPlayer,
    host: str = "0.0.0.0",
    port: int = 8001,
):
    app = create_control_server(player)

    thread = Thread(
        target=app.run,
        kwargs={
            "host": host,
            "port": port,
            "debug": False,
            "use_reloader": False,
        },
        daemon=True
    )

    thread.start()

    print(f"[control] Server started on port {port}")

    return app
