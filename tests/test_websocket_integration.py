import base64
import hashlib
import json
import os
import socket
import time
from dataclasses import dataclass

import pathway as pw
import pathwayviz as pv


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@dataclass
class _WSClient:
    sock: socket.socket
    extra: bytes = b""


def _ws_connect(host: str, port: int, path: str = "/ws") -> _WSClient:
    sock = socket.create_connection((host, port), timeout=5)
    sock.settimeout(5)

    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    sock.sendall(request.encode("ascii"))

    buf = b""
    while b"\r\n\r\n" not in buf:
        data = sock.recv(4096)
        if not data:
            raise ConnectionError("handshake failed")
        buf += data

    header_bytes, extra = buf.split(b"\r\n\r\n", 1)
    headers = header_bytes.decode("iso-8859-1").split("\r\n")
    if not headers or "101" not in headers[0]:
        raise ConnectionError(headers[0] if headers else "invalid response")

    header_map: dict[str, str] = {}
    for line in headers[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            header_map[k.strip().lower()] = v.strip()

    accept = header_map.get("sec-websocket-accept")
    expected = base64.b64encode(
        hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
    ).decode("ascii")
    if accept != expected:
        raise ConnectionError("invalid sec-websocket-accept")

    return _WSClient(sock=sock, extra=extra)


def _ws_recv_text(client: _WSClient) -> str:
    if client.extra:
        data = client.extra
        client.extra = b""
    else:
        data = b""

    while len(data) < 2:
        data += client.sock.recv(2 - len(data))

    b1 = data[0]
    b2 = data[1]
    opcode = b1 & 0x0F
    masked = (b2 & 0x80) != 0
    payload_len = b2 & 0x7F

    data = data[2:]

    if payload_len == 126:
        while len(data) < 2:
            data += client.sock.recv(2 - len(data))
        payload_len = int.from_bytes(data[:2], "big")
        data = data[2:]
    elif payload_len == 127:
        while len(data) < 8:
            data += client.sock.recv(8 - len(data))
        payload_len = int.from_bytes(data[:8], "big")
        data = data[8:]

    mask_key = b""
    if masked:
        while len(data) < 4:
            data += client.sock.recv(4 - len(data))
        mask_key = data[:4]
        data = data[4:]

    while len(data) < payload_len:
        data += client.sock.recv(payload_len - len(data))

    payload = data[:payload_len]
    remaining = data[payload_len:]
    if remaining:
        client.extra = remaining

    if masked:
        payload = bytes(payload[i] ^ mask_key[i % 4] for i in range(len(payload)))

    if opcode == 8:
        raise ConnectionError("websocket closed")
    if opcode != 1:
        raise ValueError(f"unexpected opcode {opcode}")

    return payload.decode("utf-8")


def _recv_json_until(client: _WSClient, predicate, timeout_s: float = 5.0) -> dict:
    deadline = time.time() + timeout_s
    last_err: Exception | None = None

    while time.time() < deadline:
        try:
            raw = _ws_recv_text(client)
            msg = json.loads(raw)
            if predicate(msg):
                return msg
        except (TimeoutError, json.JSONDecodeError, ValueError, ConnectionError) as e:
            last_err = e
            time.sleep(0.05)

    raise AssertionError(f"timeout waiting for message; last error: {last_err}")


def test_websocket_receives_config():
    """Test that websocket clients receive config message on connect."""
    port = _free_port()

    pv.title("WebSocket Test")
    pv.configure(embed=True)
    t = pw.debug.table_from_markdown(
        """
        | value
        | 0
        """
    )
    pv.stat(t, "value", id="ws_test_stat", title="WS Stat")

    pv.start(port)

    client: _WSClient | None = None
    try:
        time.sleep(0.2)

        client = _ws_connect("127.0.0.1", port)

        config = _recv_json_until(client, lambda m: m.get("type") == "config", timeout_s=7)
        assert config["title"] == "WebSocket Test"
        assert "ws_test_stat" in config["widgets"]
        assert config["widgets"]["ws_test_stat"]["widget_type"] == "stat"
    finally:
        if client is not None:
            client.sock.close()
        try:
            pv.stop()
        except Exception:
            pass
