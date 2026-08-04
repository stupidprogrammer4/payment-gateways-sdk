"""Parsian against a real SOAP server, over a real socket, with a real WSDL. No mocking.

``zeep`` is the SOAP layer, and zeep is driven entirely by the WSDL: it builds the request body
from the schema, so a field the SDK sends under the wrong name or the wrong type fails while zeep
serialises rather than at the bank. That makes a served WSDL the only honest way to test this —
a mocked transport would never exercise the part that actually decides what goes on the wire.

So this module serves PEC's two contracts (``tests/wsdl.py``) from an ASMX-shaped HTTP server on a
real port, lets zeep fetch and parse them, and drives both engines end to end against it.
"""

import asyncio
import re
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from xml.etree import ElementTree as ET

import pytest

from payment_gateways_sdk import (
    ConfigurationError,
    GatewayError,
    ParsianAsync,
    ParsianSync,
    PaymentRequest,
    PaymentVerification,
)
from payment_gateways_sdk.gateways.parsian import ParsianConfirmDetails, ParsianSaleDetails
from payment_gateways_sdk.gateways.parsian import async_engine as parsian_async
from payment_gateways_sdk.gateways.parsian import helpers as parsian_helpers
from payment_gateways_sdk.gateways.parsian import sync_engine as parsian_sync
from tests.wsdl import CONFIRM_NS, SALE_NS, confirm_wsdl, sale_wsdl

SOAP_ENV = "http://schemas.xmlsoap.org/soap/envelope/"

AMOUNT = 50_000
CALLBACK = "https://shop.example/payments/parsian/callback"
ORDER_ID = "1001"
PIN = "TestLoginAccount"

SALE_PATH = "/NewIPGServices/Sale/SaleService.asmx"
CONFIRM_PATH = "/NewIPGServices/Confirm/ConfirmService.asmx"


class Recorder:
    """What the server saw, and what it should answer with."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.wsdl_fetches = 0
        self.sale_status = 0
        self.sale_token = 90_100_200
        self.sale_message = "Successful"
        self.confirm_status = 0
        self.confirm_rrn = "987654321"
        self.mode = "ok"  # "ok" | "fault"
        self.delay = 0.0
        self.lock = threading.Lock()


def _make_handler(rec: Recorder) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        base_url = ""

        def log_message(self, format: str, *args: Any) -> None:
            """Silence the server's stderr logging so pytest output stays readable."""

        def _send(self, payload: str, status: int = 200, content_type: str = "text/xml") -> None:
            body = payload.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            """Serve the WSDL. This is the request zeep makes before it can do anything."""
            with rec.lock:
                rec.wsdl_fetches += 1
            if self.path.startswith(SALE_PATH):
                self._send(sale_wsdl(f"{self.base_url}{SALE_PATH}"))
            elif self.path.startswith(CONFIRM_PATH):
                self._send(confirm_wsdl(f"{self.base_url}{CONFIRM_PATH}"))
            else:
                self._send("not found", status=404, content_type="text/plain")

        def do_POST(self) -> None:
            if rec.delay:
                time.sleep(rec.delay)

            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            content_type = self.headers.get("Content-Type", "")
            action = (self.headers.get("SOAPAction") or "").strip('"')

            # ASMX rejects both of these before its own code runs.
            if "text/xml" not in content_type:
                self._send(f"expected text/xml, got {content_type}", 415, "text/plain")
                return
            if not action:
                self._send("missing SOAPAction", 500, "text/plain")
                return

            root = ET.fromstring(raw)
            body = root.find(f"{{{SOAP_ENV}}}Body")
            assert body is not None and len(body) == 1
            call = body[0]
            match = re.fullmatch(r"\{(?P<ns>[^}]+)\}(?P<op>.+)", call.tag)
            assert match is not None
            namespace, operation = match.group("ns"), match.group("op")

            expected_ns = SALE_NS if self.path.startswith(SALE_PATH) else CONFIRM_NS
            if namespace != expected_ns:
                self._send(f"unknown namespace {namespace}", 500, "text/plain")
                return
            if action != f"{expected_ns}/{operation}":
                self._send(f"SOAPAction {action} does not match {operation}", 500, "text/plain")
                return

            request_data = call.find(f"{{{namespace}}}requestData")
            assert request_data is not None
            fields = {
                re.sub(r"^\{[^}]+\}", "", child.tag): (child.text or "") for child in request_data
            }
            with rec.lock:
                rec.requests.append(
                    {
                        "path": self.path,
                        "operation": operation,
                        "namespace": namespace,
                        "soap_action": action,
                        "fields": fields,
                        "raw": raw,
                    }
                )

            if rec.mode == "fault":
                self._send(
                    f'<?xml version="1.0"?><soap:Envelope xmlns:soap="{SOAP_ENV}"><soap:Body>'
                    "<soap:Fault><faultcode>soap:Server</faultcode>"
                    "<faultstring>System.NullReferenceException: Object reference not set."
                    "</faultstring></soap:Fault></soap:Body></soap:Envelope>",
                    status=500,
                )
                return

            if operation == "SalePaymentRequest":
                self._send(
                    f'<?xml version="1.0" encoding="utf-8"?>'
                    f'<soap:Envelope xmlns:soap="{SOAP_ENV}"><soap:Body>'
                    f'<SalePaymentRequestResponse xmlns="{SALE_NS}">'
                    f"<SalePaymentRequestResult>"
                    f"<Status>{rec.sale_status}</Status>"
                    f"<Message>{rec.sale_message}</Message>"
                    f"<Token>{rec.sale_token}</Token>"
                    f"</SalePaymentRequestResult>"
                    f"</SalePaymentRequestResponse></soap:Body></soap:Envelope>"
                )
            else:
                self._send(
                    f'<?xml version="1.0" encoding="utf-8"?>'
                    f'<soap:Envelope xmlns:soap="{SOAP_ENV}"><soap:Body>'
                    f'<ConfirmPaymentResponse xmlns="{CONFIRM_NS}">'
                    f"<ConfirmPaymentResult>"
                    f"<Status>{rec.confirm_status}</Status>"
                    f"<CardNumberMasked>622106******1234</CardNumberMasked>"
                    f"<Token>{rec.sale_token}</Token>"
                    f"<RRN>{rec.confirm_rrn}</RRN>"
                    f"</ConfirmPaymentResult>"
                    f"</ConfirmPaymentResponse></soap:Body></soap:Envelope>"
                )

    return Handler


@pytest.fixture
def pec(monkeypatch: pytest.MonkeyPatch) -> Iterator[Recorder]:
    """A real PEC-shaped server serving real WSDLs, with both engines pointed at it."""
    recorder = Recorder()
    handler = _make_handler(recorder)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    handler.base_url = base  # type: ignore[attr-defined]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # zeep caches parsed WSDLs per client, and the SDK caches clients per (wsdl, proxy). Each test
    # gets a fresh port, so the cache has to be cleared or it would answer with the previous run's
    # client — pointing at a server that is already shut down.
    parsian_helpers.clear_client_cache()
    for module in (parsian_sync, parsian_async):
        monkeypatch.setattr(module, "SALE_WSDL", f"{base}{SALE_PATH}?wsdl")
        monkeypatch.setattr(module, "CONFIRM_WSDL", f"{base}{CONFIRM_PATH}?wsdl")

    try:
        yield recorder
    finally:
        parsian_helpers.clear_client_cache()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def a_request(**overrides: Any) -> PaymentRequest:
    fields: dict[str, Any] = {
        "amount": AMOUNT,
        "callback_url": CALLBACK,
        "order_id": ORDER_ID,
        "description": "Order 1001",
    }
    fields.update(overrides)
    return PaymentRequest(**fields)


def a_verification(authority: str = "90100200", **extra: object) -> PaymentVerification:
    return PaymentVerification(
        authority=authority, amount=AMOUNT, order_id=ORDER_ID, extra=dict(extra)
    )


# ---------------------------------------------------------------------------------------------
# The wire format a real SOAP server accepts
# ---------------------------------------------------------------------------------------------


def test_zeep_fetches_the_wsdl_and_sends_an_accepted_request(pec: Recorder) -> None:
    payment = ParsianSync(pin=PIN).make_payment_request(a_request())

    assert pec.wsdl_fetches >= 1, "zeep never fetched the WSDL"
    assert payment.authority == "90100200"
    assert payment.redirect_url == "https://pec.shaparak.ir/NewIPG/?token=90100200"
    assert isinstance(payment.details, ParsianSaleDetails)
    assert payment.details.status == 0
    assert payment.details.token == 90_100_200

    sent = pec.requests[0]
    assert sent["operation"] == "SalePaymentRequest"
    assert sent["namespace"] == SALE_NS
    assert sent["soap_action"] == f"{SALE_NS}/SalePaymentRequest"
    assert sent["fields"] == {
        "LoginAccount": PIN,
        "Amount": str(AMOUNT),
        "OrderId": ORDER_ID,
        "CallBackUrl": CALLBACK,
        "AdditionalData": "Order 1001",
        "Originator": "",
    }


def test_fields_are_serialised_in_the_order_the_schema_declares(pec: Recorder) -> None:
    """An ASMX ``s:sequence`` is ordered; zeep honours it, and a hand-built body might not."""
    ParsianSync(pin=PIN).make_payment_request(a_request())
    assert list(pec.requests[0]["fields"]) == [
        "LoginAccount",
        "Amount",
        "OrderId",
        "CallBackUrl",
        "AdditionalData",
        "Originator",
    ]


def test_persian_and_xml_special_characters_survive_the_round_trip(pec: Recorder) -> None:
    """A description is caller-controlled text; unescaped, it would corrupt the envelope."""
    hostile = "سفارش «۱۰۰۱» — Ben & Jerry's <b>50%</b>"  # noqa: RUF001 — Persian digits are the point
    ParsianSync(pin=PIN).make_payment_request(a_request(description=hostile))
    assert pec.requests[0]["fields"]["AdditionalData"] == hostile
    assert b"&amp;" in pec.requests[0]["raw"]


def test_both_engines_send_the_same_body(pec: Recorder) -> None:
    """The engines must differ only in how the bytes are delivered, never in what they are."""
    ParsianSync(pin=PIN).make_payment_request(a_request())
    asyncio.run(ParsianAsync(pin=PIN).make_payment_request(a_request()))
    assert pec.requests[0]["fields"] == pec.requests[1]["fields"]
    assert pec.requests[0]["soap_action"] == pec.requests[1]["soap_action"]


def test_confirm_request_is_scoped_to_the_token(pec: Recorder) -> None:
    verified = ParsianSync(pin=PIN).verify_payment(a_verification())

    assert verified.success
    assert verified.reference == "987654321"
    assert isinstance(verified.details, ParsianConfirmDetails)
    assert verified.details.card_number_masked == "622106******1234"

    sent = pec.requests[0]
    assert sent["path"].startswith(CONFIRM_PATH)
    assert sent["operation"] == "ConfirmPayment"
    assert sent["soap_action"] == f"{CONFIRM_NS}/ConfirmPayment"
    assert sent["fields"] == {"LoginAccount": PIN, "Token": "90100200"}


# ---------------------------------------------------------------------------------------------
# Both engines, end to end
# ---------------------------------------------------------------------------------------------


def test_full_payment_cycle_sync(pec: Recorder) -> None:
    gateway = ParsianSync(pin=PIN)
    payment = gateway.make_payment_request(a_request())
    verified = gateway.verify_payment(
        PaymentVerification(authority=payment.authority, amount=AMOUNT, order_id=ORDER_ID)
    )
    assert verified.success
    assert [r["operation"] for r in pec.requests] == ["SalePaymentRequest", "ConfirmPayment"]


async def test_full_payment_cycle_async(pec: Recorder) -> None:
    gateway = ParsianAsync(pin=PIN)
    payment = await gateway.make_payment_request(a_request())
    verified = await gateway.verify_payment(
        PaymentVerification(authority=payment.authority, amount=AMOUNT, order_id=ORDER_ID)
    )
    assert verified.success
    assert verified.amount == AMOUNT
    assert [r["operation"] for r in pec.requests] == ["SalePaymentRequest", "ConfirmPayment"]


# ---------------------------------------------------------------------------------------------
# The async engine is actually async
# ---------------------------------------------------------------------------------------------


async def test_concurrent_soap_calls_do_not_serialise(pec: Recorder) -> None:
    """Eight calls against a server that sleeps 300ms each.

    Serialised that is 2.4 seconds; concurrently it is a shade over 300ms. The client is warmed up
    first so the blocking WSDL parse is not being measured — that cost is real, but it is paid once
    per process, not per payment.
    """
    gateway = ParsianAsync(pin=PIN)
    gateway.warm_up()
    pec.delay = 0.3

    started = time.monotonic()
    payments = await asyncio.gather(
        *(gateway.make_payment_request(a_request(order_id=str(2000 + i))) for i in range(8))
    )
    elapsed = time.monotonic() - started

    assert len(payments) == 8
    assert all(p.authority == "90100200" for p in payments)
    assert len(pec.requests) == 8
    assert elapsed < 1.5, f"8 concurrent SOAP calls took {elapsed:.2f}s — they serialised"


async def test_the_event_loop_stays_responsive_during_a_soap_call(pec: Recorder) -> None:
    """A blocking call would starve this ticker; a real await lets it run throughout."""
    gateway = ParsianAsync(pin=PIN)
    gateway.warm_up()
    pec.delay = 0.4
    ticks = 0

    async def tick() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.02)
            ticks += 1

    ticker = asyncio.create_task(tick())
    try:
        await gateway.make_payment_request(a_request())
    finally:
        ticker.cancel()

    assert ticks > 5, f"the loop only ticked {ticks} times — the SOAP call blocked it"


def test_the_wsdl_is_parsed_once_per_process_not_once_per_payment(pec: Recorder) -> None:
    """Client caching is what keeps zeep's blocking WSDL fetch off the money path."""
    gateway = ParsianSync(pin=PIN)
    for i in range(4):
        gateway.make_payment_request(a_request(order_id=str(5000 + i)))
    assert len(pec.requests) == 4
    assert pec.wsdl_fetches == 1, f"the WSDL was fetched {pec.wsdl_fetches} times"


# ---------------------------------------------------------------------------------------------
# What a real server does when things go wrong
# ---------------------------------------------------------------------------------------------


def test_gateway_decline_over_the_wire(pec: Recorder) -> None:
    pec.sale_status = -138
    pec.sale_message = "Canceled By User"
    pec.sale_token = 0
    with pytest.raises(GatewayError, match="parsian declined") as exc:
        ParsianSync(pin=PIN).make_payment_request(a_request())
    assert "Canceled By User" in str(exc.value)


def test_soap_fault_over_the_wire(pec: Recorder) -> None:
    pec.mode = "fault"
    with pytest.raises(GatewayError, match="parsian request failed"):
        ParsianSync(pin=PIN).make_payment_request(a_request())


async def test_verify_never_raises_over_the_wire(pec: Recorder) -> None:
    """A returning payer must meet a result, not an exception — even on a fault."""
    pec.mode = "fault"
    verified = await ParsianAsync(pin=PIN).verify_payment(a_verification())
    assert not verified.success
    assert verified.message


def test_confirm_decline_over_the_wire(pec: Recorder) -> None:
    pec.confirm_status = -1533
    verified = ParsianSync(pin=PIN).verify_payment(a_verification())
    assert not verified.success
    assert "-1533" in (verified.message or "")


def test_a_dead_server_is_a_clean_error(pec: Recorder, monkeypatch: pytest.MonkeyPatch) -> None:
    """Nothing is listening there — the failure must name the gateway, not leak a zeep traceback."""
    parsian_helpers.clear_client_cache()
    monkeypatch.setattr(parsian_sync, "SALE_WSDL", "http://127.0.0.1:1/Sale.asmx?wsdl")
    with pytest.raises(GatewayError, match="parsian"):
        ParsianSync(pin=PIN).make_payment_request(a_request())


def test_a_non_numeric_order_id_is_refused_before_any_call(pec: Recorder) -> None:
    with pytest.raises(ConfigurationError):
        ParsianSync(pin=PIN).make_payment_request(a_request(order_id="abc"))
    assert pec.requests == []


def test_parsian_needs_a_pin() -> None:
    with pytest.raises(ConfigurationError, match="pin"):
        ParsianSync(pin="")


# ---------------------------------------------------------------------------------------------
# The callback still guards the confirm call
# ---------------------------------------------------------------------------------------------


def test_a_declined_callback_stops_the_confirm_call_reaching_the_server(pec: Recorder) -> None:
    """The bank already said the payer did not pay, so nothing should be asked of it."""
    verified = ParsianSync(pin=PIN).verify_payment(a_verification(status="-1", RRN="0"))
    assert not verified.success
    assert "callback status" in (verified.message or "")
    assert pec.requests == []


def test_a_zero_callback_status_lets_the_confirm_call_through(pec: Recorder) -> None:
    verified = ParsianSync(pin=PIN).verify_payment(a_verification(Token="90100200", status="0"))
    assert verified.success
    assert len(pec.requests) == 1


def test_a_non_numeric_token_is_refused(pec: Recorder) -> None:
    verified = ParsianSync(pin=PIN).verify_payment(a_verification(authority="not-a-number"))
    assert not verified.success
    assert "bad token" in (verified.message or "")
    assert pec.requests == []
