"""Local certificate editor server — stdlib HTTP + WebSocket (no Flask)."""
import base64
import hashlib
import json
import os
import socket
import struct
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from certificate_pdf import (
    DEFAULT_TEMPLATE,
    generate_certificate_pdf,
    load_template_data,
    render_template_png,
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(APP_DIR, "certificate_web")
CERTIFICATES_DIR = os.path.join(APP_DIR, "certificates")

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

_server = None
_server_thread = None
_server_port = None
_template_path = DEFAULT_TEMPLATE


def _find_free_port(start=8765):
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found for certificate web editor")


def _ws_accept_key(sec_key):
    digest = hashlib.sha1((sec_key + WS_GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def _ws_read_message(read_file):
    header = read_file.read(2)
    if not header or len(header) < 2:
        return None
    b1, b2 = header[0], header[1]
    opcode = b1 & 0x0F
    masked = (b2 >> 7) & 1
    length = b2 & 0x7F

    if length == 126:
        length = struct.unpack("!H", read_file.read(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", read_file.read(8))[0]

    mask = read_file.read(4) if masked else None
    payload = read_file.read(length)
    if masked and mask:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))

    if opcode == 0x8:
        return None
    if opcode == 0x9:
        return "__PING__"
    if opcode != 0x1:
        return None
    return payload.decode("utf-8")


def _ws_send_text(write_file, text):
    data = text.encode("utf-8")
    frame = bytearray([0x81])
    length = len(data)
    if length <= 125:
        frame.append(length)
    elif length <= 65535:
        frame.append(126)
        frame.extend(struct.pack("!H", length))
    else:
        frame.append(127)
        frame.extend(struct.pack("!Q", length))
    frame.extend(data)
    write_file.write(frame)
    write_file.flush()


def _ws_send_pong(write_file):
    write_file.write(b"\x8A\x00")
    write_file.flush()


def _handle_ws_action(message):
    global _template_path
    action = message.get("action")
    req_id = message.get("id")

    def reply(payload, ok=True, status=200):
        out = {"id": req_id, "ok": ok, **payload}
        if not ok:
            out["error"] = payload.get("error", "Request failed")
        return out

    try:
        if action == "get_template":
            template = message.get("templatePath") or _template_path
            data = load_template_data(template)
            _template_path = data["templatePath"]
            return reply(data)

        if action == "generate":
            template_path = message.get("templatePath") or _template_path
            fields = message.get("fields") or []
            filename = (message.get("filename") or "certificate.pdf").strip()
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"
            output_path = os.path.join(CERTIFICATES_DIR, os.path.basename(filename))
            generate_certificate_pdf(template_path, fields, output_path)
            return reply({
                "path": output_path,
                "filename": os.path.basename(output_path),
                "message": f"Certificate saved to {output_path}",
            })

        return reply({"error": f"Unknown action: {action}"}, ok=False)
    except Exception as exc:
        return reply({"error": str(exc)}, ok=False)


class CertificateRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format, *args):
        return

    def _serve_static(self, rel_path, content_type):
        safe_path = os.path.normpath(rel_path).lstrip(os.sep)
        file_path = os.path.join(WEB_DIR, safe_path)
        if not file_path.startswith(WEB_DIR) or not os.path.isfile(file_path):
            self.send_error(404)
            return
        with open(file_path, "rb") as handle:
            data = handle.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_websocket(self):
        sec_key = self.headers.get("Sec-WebSocket-Key")
        if not sec_key:
            self.send_error(400)
            return

        accept_key = _ws_accept_key(sec_key)
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept_key)
        self.end_headers()

        while True:
            raw = _ws_read_message(self.rfile)
            if raw is None:
                break
            if raw == "__PING__":
                _ws_send_pong(self.wfile)
                continue
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                response = {"ok": False, "error": "Invalid JSON"}
                _ws_send_text(self.wfile, json.dumps(response))
                continue
            response = _handle_ws_action(message)
            _ws_send_text(self.wfile, json.dumps(response))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/ws":
            if self.headers.get("Upgrade", "").lower() == "websocket":
                self._handle_websocket()
            else:
                self.send_error(426)
            return

        if path == "/template.png":
            try:
                png = render_template_png(_template_path)
            except Exception as exc:
                self.send_error(500, str(exc))
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(png)))
            self.end_headers()
            self.wfile.write(png)
            return

        if path in ("/", "/index.html"):
            self._serve_static("index.html", "text/html; charset=utf-8")
            return

        self.send_error(404)


def start_server(port=None):
    global _server, _server_thread, _server_port
    if _server_thread and _server_thread.is_alive():
        return _server_port

    _server_port = port or _find_free_port()
    _server = ThreadingHTTPServer(("127.0.0.1", _server_port), CertificateRequestHandler)

    def run():
        _server.serve_forever(poll_interval=0.5)

    _server_thread = threading.Thread(target=run, daemon=True)
    _server_thread.start()
    return _server_port


def open_certificate_web_editor():
    port = start_server()
    url = f"http://127.0.0.1:{port}/"
    webbrowser.open(url)
    return url
