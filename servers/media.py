import os

from functools import partial
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread

CHUNK_SIZE = 64 * 1024


class RangeRequestHandler(SimpleHTTPRequestHandler):
    """
    This class extends SimpleHTTPRequestHandler to support HTTP Range requests.
    This is a key feature to allow seeking within video files, which is essential
    for Chromecast playback.
    """

    def send_head(self):
        path = self.translate_path(self.path)

        if not os.path.isfile(path):
            return super().send_head()

        range_header = self.headers.get("Range")
        if not range_header:
            self._range = None
            return super().send_head()

        file_size = os.path.getsize(path)
        try:
            start, end = self._parse_range(range_header, file_size)
        except ValueError:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{file_size}")
            self.end_headers()
            return None

        f = open(path, "rb")
        f.seek(start)

        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()

        self._range = (start, end - start + 1)
        return f

    @staticmethod
    def _parse_range(range_header: str, file_size: int) -> tuple[int, int]:
        units, _, range_spec = range_header.partition("=")
        if units != "bytes":
            raise ValueError("Range unit not supported (should be bytes)")

        start_str, _, end_str = range_spec.partition("-")
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        end = min(end, file_size - 1)

        if start > end or start < 0:
            raise ValueError(f"Invalid range specified. Should be 0 <= {start} <= {end}")

        return start, end

    def copyfile(self, source, outputfile):
        try:
            if getattr(self, "_range", None) is None:
                return super().copyfile(source, outputfile)

            remaining = self._range[1]
            while remaining > 0:
                chunk = source.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    break
                outputfile.write(chunk)
                remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            # Chromecast cut the connection
            # not a real error, just a client disconnect (e.g., pause or change video)
            pass

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def log_message(self, format, *args):
        """ Explicit log of each request
        File name, status, if included range
        """
        print(f"[media] {self.address_string()} -> {format % args}")


def run_server(movies_dir: Path, port: int = 8000):
    handler = partial(
        RangeRequestHandler,
        directory=str(movies_dir)
    )

    server = ThreadingHTTPServer(("0.0.0.0", port), handler)

    thread = Thread(
        target=server.serve_forever,
        daemon=True
    )

    thread.start()

    print(f"[media] Server started on port {port}")
    return server
