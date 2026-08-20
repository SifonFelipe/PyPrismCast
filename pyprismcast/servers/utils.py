import socket
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MOVIES_DIR = BASE_DIR / "movies"
WEB_DIR = BASE_DIR / "web"

MEDIA_PORT = 8000
CONTROL_PORT = 8001
HOST = "0.0.0.0"


def get_local_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    finally:
        sock.close()
