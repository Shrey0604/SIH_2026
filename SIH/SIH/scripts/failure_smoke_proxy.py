#!/usr/bin/env python3
"""REST-only proxy used to prove the frontend WebSocket fallback."""

from __future__ import annotations

import http.server
import urllib.error
import urllib.request


UPSTREAM = "http://127.0.0.1:8000"


class RestOnlyHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib handler API
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.headers.get("Upgrade", "").casefold() == "websocket":
            self.send_error(503, "WebSocket deliberately unavailable for failure smoke")
            return
        self._forward()

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        self._forward()

    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _forward(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else None
        request = urllib.request.Request(
            f"{UPSTREAM}{self.path}",
            method=self.command,
            data=body,
            headers={"Content-Type": self.headers.get("Content-Type", "application/json")},
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read()
                status = response.status
                content_type = response.headers.get("Content-Type", "application/octet-stream")
        except urllib.error.HTTPError as error:
            payload = error.read()
            status = error.code
            content_type = error.headers.get("Content-Type", "application/json")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self._cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("127.0.0.1", 8003), RestOnlyHandler).serve_forever()

