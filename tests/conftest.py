"""A real HTTP server that every gateway test runs against.

There is no mocking library anywhere in this suite. ``respx`` patched httpx in-process, which went
away with httpx; rather than swapping it for ``aioresponses`` plus ``responses`` — one mock library
per engine, each faking a different client — the tests drive both engines over a real socket.

That is strictly stronger. An in-process mock will accept a request no server would: wrong content
type, unencoded body, a header the gateway dispatches on quietly missing. This server sees exactly
what the SDK put on the wire, and both engines are held to the same bytes.

Each gateway's endpoint constants are repointed at this server. They are patched where they are
*used* — some engines import a URL directly, others reach it through ``helpers`` — because a
module-level ``from … import NAME`` binds the value at import time, so patching the ``constants``
module alone would change nothing.
"""

import json
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from payment_gateways_sdk.gateways.sadad import async_engine as sadad_async
from payment_gateways_sdk.gateways.sadad import sync_engine as sadad_sync
from payment_gateways_sdk.gateways.sepehr import async_engine as sepehr_async
from payment_gateways_sdk.gateways.sepehr import sync_engine as sepehr_sync
from payment_gateways_sdk.gateways.top import async_engine as top_async
from payment_gateways_sdk.gateways.top import sync_engine as top_sync
from payment_gateways_sdk.gateways.yektapay import async_engine as yektapay_async
from payment_gateways_sdk.gateways.yektapay import helpers as yektapay_helpers
from payment_gateways_sdk.gateways.yektapay import sync_engine as yektapay_sync
from payment_gateways_sdk.gateways.zarinpal import helpers as zarinpal_helpers
from payment_gateways_sdk.gateways.zibal import async_engine as zibal_async
from payment_gateways_sdk.gateways.zibal import sync_engine as zibal_sync

# The path each gateway operation is served on, and where its URL constant has to be patched.
# ``(attribute, [modules that imported it])``.
ROUTES: dict[str, tuple[str, list[Any]]] = {
    "/zarinpal/request": ("REQUEST_URL", [zarinpal_helpers]),
    "/zarinpal/verify": ("VERIFY_URL", [zarinpal_helpers]),
    "/zibal/request": ("REQUEST_URL", [zibal_sync, zibal_async]),
    "/zibal/verify": ("VERIFY_URL", [zibal_sync, zibal_async]),
    "/yektapay/request": ("REQUEST_URL", [yektapay_sync, yektapay_async]),
    "/top/request": ("REQUEST_URL", [top_sync, top_async]),
    "/top/verify": ("VERIFY_URL", [top_sync, top_async]),
    "/sepehr/token": ("TOKEN_URL", [sepehr_sync, sepehr_async]),
    "/sepehr/advice": ("ADVICE_URL", [sepehr_sync, sepehr_async]),
    "/sadad/request": ("REQUEST_URL", [sadad_sync, sadad_async]),
    "/sadad/verify": ("VERIFY_URL", [sadad_sync, sadad_async]),
}

#: Yektapay's verify URL is a template with the order uuid in it, so it is handled separately.
YEKTAPAY_VERIFY_TEMPLATE = "/yektapay/verify/{authority}/"


@dataclass
class Exchange:
    """One request the server actually received."""

    path: str
    headers: dict[str, str]
    body: bytes

    @property
    def json(self) -> dict[str, Any]:
        return dict(json.loads(self.body.decode() or "{}"))


@dataclass
class Reply:
    """What the server should answer with."""

    payload: Any = field(default_factory=dict)
    status: int = 200
    raw_text: str | None = None
    content_type: str = "application/json"


class Stub:
    """Controls the server: what it answers, and what it saw."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.exchanges: list[Exchange] = []
        self.replies: dict[str, Reply] = {}
        self.delay = 0.0
        self.lock = threading.Lock()

    def reply(self, path: str, payload: Any, *, status: int = 200) -> None:
        """Answer ``path`` with this JSON body."""
        self.replies[path] = Reply(payload=payload, status=status)

    def reply_text(self, path: str, text: str, *, status: int = 200) -> None:
        """Answer ``path`` with a body that is not JSON at all."""
        self.replies[path] = Reply(raw_text=text, status=status, content_type="text/html")

    def last(self, path: str | None = None) -> Exchange:
        matching = [e for e in self.exchanges if path is None or e.path.startswith(path)]
        assert matching, f"no request was made to {path!r} (saw {[e.path for e in self.exchanges]})"
        return matching[-1]

    @property
    def paths(self) -> list[str]:
        return [e.path for e in self.exchanges]


def _make_handler(stub: Stub) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: Any) -> None:
            """Silence the server's stderr logging so pytest output stays readable."""

        def do_POST(self) -> None:  # BaseHTTPRequestHandler's required method name
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length)
            with stub.lock:
                stub.exchanges.append(
                    Exchange(
                        path=self.path,
                        headers={k.lower(): v for k, v in self.headers.items()},
                        body=body,
                    )
                )
            reply = stub.replies.get(self.path)
            if reply is None:
                # Prefix match, for Yektapay's uuid-in-the-path verify endpoint.
                for path, candidate in stub.replies.items():
                    if self.path.startswith(path.rstrip("*")):
                        reply = candidate
                        break
            if reply is None:
                payload = b'{"error": "no stubbed reply"}'
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

            text = reply.raw_text if reply.raw_text is not None else json.dumps(reply.payload)
            encoded = text.encode()
            self.send_response(reply.status)
            self.send_header("Content-Type", reply.content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return Handler


@pytest.fixture
def stub(monkeypatch: pytest.MonkeyPatch) -> Iterator[Stub]:
    """A live HTTP server with every gateway's endpoints pointed at it."""
    controller = Stub("")
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(controller))
    controller.base_url = f"http://127.0.0.1:{server.server_address[1]}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    for path, (attribute, modules) in ROUTES.items():
        for module in modules:
            monkeypatch.setattr(module, attribute, f"{controller.base_url}{path}")
    monkeypatch.setattr(
        yektapay_helpers, "VERIFY_URL", f"{controller.base_url}{YEKTAPAY_VERIFY_TEMPLATE}"
    )

    try:
        yield controller
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
