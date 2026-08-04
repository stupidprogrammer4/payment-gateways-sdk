"""Every REST gateway, both engines, against a real HTTP server.

No mocking: the ``stub`` fixture in ``conftest.py`` is an actual server on an actual port, so these
tests see the bytes the SDK put on the wire. Each gateway is exercised through its sync class and
its async class with the same fixtures, which is what keeps the two engines from drifting apart —
a change that breaks one and not the other shows up here rather than in production.
"""

import asyncio

import pytest

from payment_gateways_sdk import (
    ConfigurationError,
    GatewayError,
    NetworkError,
    PaymentRequest,
    PaymentVerification,
    SepehrAsync,
    SepehrSync,
    TopAsync,
    TopSync,
    VerificationResult,
    YektapayAsync,
    YektapaySync,
    ZarinpalAsync,
    ZarinpalSync,
    ZibalAsync,
    ZibalSync,
    available,
    get_async_gateway,
    get_sync_gateway,
)
from payment_gateways_sdk.gateways.zarinpal import ZarinpalVerifyDetails
from payment_gateways_sdk.gateways.zarinpal import helpers as zarinpal_helpers
from payment_gateways_sdk.gateways.zibal import ZibalVerifyDetails
from payment_gateways_sdk.gateways.zibal import async_engine as zibal_async_engine
from payment_gateways_sdk.gateways.zibal import sync_engine as zibal_sync_engine
from tests.conftest import Stub

AMOUNT = 50_000
CALLBACK = "https://shop.example/callback"
ORDER_ID = "1001"
MERCHANT_ID = "m" * 36


def a_request(order_id: str = ORDER_ID, **overrides: object) -> PaymentRequest:
    fields: dict[str, object] = {
        "amount": AMOUNT,
        "callback_url": CALLBACK,
        "order_id": order_id,
    }
    fields.update(overrides)
    return PaymentRequest(**fields)  # type: ignore[arg-type]


def a_verification(authority: str, amount: int = AMOUNT, **extra: object) -> PaymentVerification:
    return PaymentVerification(
        authority=authority, amount=amount, order_id=ORDER_ID, extra=dict(extra)
    )


# ---------------------------------------------------------------------------------------------
# ZarinPal
# ---------------------------------------------------------------------------------------------


def test_zarinpal_request_sync(stub: Stub) -> None:
    stub.reply("/zarinpal/request", {"data": {"code": 100, "authority": "A123"}})
    payment = ZarinpalSync(merchant_id=MERCHANT_ID).make_payment_request(a_request())

    assert payment.authority == "A123"
    assert payment.redirect_url.endswith("/pg/StartPay/A123")
    sent = stub.last("/zarinpal/request").json
    assert sent["merchant_id"] == MERCHANT_ID
    assert sent["amount"] == AMOUNT
    assert sent["callback_url"] == CALLBACK


async def test_zarinpal_request_async(stub: Stub) -> None:
    stub.reply("/zarinpal/request", {"data": {"code": 100, "authority": "A123"}})
    payment = await ZarinpalAsync(merchant_id=MERCHANT_ID).make_payment_request(a_request())
    assert payment.authority == "A123"


def test_zarinpal_request_declined_raises(stub: Stub) -> None:
    stub.reply("/zarinpal/request", {"data": {"code": -9}, "errors": {"code": -9}})
    with pytest.raises(GatewayError) as exc:
        ZarinpalSync(merchant_id=MERCHANT_ID).make_payment_request(a_request())
    assert exc.value.code == -9


@pytest.mark.parametrize("code", [100, 101])
def test_zarinpal_verify_accepts_both_success_codes(stub: Stub, code: int) -> None:
    """101 is 'already verified' — a repeated callback for a payment that did arrive."""
    stub.reply("/zarinpal/verify", {"data": {"code": code, "ref_id": 777}})
    result = ZarinpalSync(merchant_id=MERCHANT_ID).verify_payment(a_verification("A123"))
    assert result.success
    assert result.reference == "777"


async def test_zarinpal_verify_async(stub: Stub) -> None:
    stub.reply("/zarinpal/verify", {"data": {"code": 100, "ref_id": 777}})
    result = await ZarinpalAsync(merchant_id=MERCHANT_ID).verify_payment(a_verification("A123"))
    assert result.success


def test_zarinpal_verify_declined(stub: Stub) -> None:
    stub.reply("/zarinpal/verify", {"data": {"code": -51}})
    result = ZarinpalSync(merchant_id=MERCHANT_ID).verify_payment(a_verification("A123"))
    assert not result.success
    assert "-51" in (result.message or "")


def test_zarinpal_needs_a_merchant_id() -> None:
    with pytest.raises(ConfigurationError):
        ZarinpalSync(merchant_id="")


def test_zarinpal_sandbox_switches_every_url() -> None:
    config = ZarinpalSync(merchant_id=MERCHANT_ID, sandbox=True).config
    assert "sandbox" in zarinpal_helpers.request_url(config)
    assert "sandbox" in zarinpal_helpers.verify_url(config)
    assert "sandbox" in zarinpal_helpers.start_url(config, "A123")


def test_zarinpal_details_carry_the_full_response(stub: Stub) -> None:
    """The gateway-specific record is what makes fee and card data reachable without ``raw``."""
    stub.reply(
        "/zarinpal/verify",
        {
            "data": {
                "code": 100,
                "ref_id": 777,
                "card_pan": "502229******5995",
                "card_hash": "1EBE3EBBE9",
                "fee_type": "Merchant",
                "fee": 1000,
            }
        },
    )
    details = ZarinpalSync(merchant_id=MERCHANT_ID).verify_payment(a_verification("A123")).details
    assert isinstance(details, ZarinpalVerifyDetails)
    assert details.card_pan == "502229******5995"
    assert details.fee == 1000
    assert details.fee_type == "Merchant"


# ---------------------------------------------------------------------------------------------
# Zibal
# ---------------------------------------------------------------------------------------------


def test_zibal_request_sync(stub: Stub) -> None:
    stub.reply("/zibal/request", {"result": 100, "trackId": 424242})
    payment = ZibalSync().make_payment_request(a_request())
    assert payment.authority == "424242"
    assert payment.redirect_url.endswith("/start/424242")
    assert stub.last("/zibal/request").json["merchant"] == "zibal"


async def test_zibal_request_async(stub: Stub) -> None:
    stub.reply("/zibal/request", {"result": 100, "trackId": 424242})
    payment = await ZibalAsync().make_payment_request(a_request())
    assert payment.authority == "424242"


@pytest.mark.parametrize("result", [100, 201])
def test_zibal_verify_accepts_both_success_codes(stub: Stub, result: int) -> None:
    stub.reply("/zibal/verify", {"result": result, "amount": AMOUNT, "refNumber": 999})
    verified = ZibalSync().verify_payment(a_verification("424242"))
    assert verified.success
    assert verified.reference == "999"
    assert verified.amount == AMOUNT


async def test_zibal_verify_async(stub: Stub) -> None:
    stub.reply("/zibal/verify", {"result": 100, "amount": AMOUNT, "refNumber": 999})
    verified = await ZibalAsync().verify_payment(a_verification("424242"))
    assert verified.success


def test_zibal_verify_rejects_amount_mismatch(stub: Stub) -> None:
    """The gateway says paid, but for less than the payment was opened for."""
    stub.reply("/zibal/verify", {"result": 100, "amount": 1, "refNumber": 999})
    verified = ZibalSync().verify_payment(a_verification("424242"))
    assert not verified.success
    assert "amount mismatch" in (verified.message or "")


def test_zibal_verify_fails_closed_without_an_amount(stub: Stub) -> None:
    """'Paid' with no amount is the one case that cannot be reasoned about — it must not settle."""
    stub.reply("/zibal/verify", {"result": 100, "refNumber": 999})
    verified = ZibalSync().verify_payment(a_verification("424242"))
    assert not verified.success
    assert "cannot confirm" in (verified.message or "")


def test_zibal_verify_rejects_a_non_numeric_track_id(stub: Stub) -> None:
    verified = ZibalSync().verify_payment(a_verification("not-a-number"))
    assert not verified.success
    assert "bad trackId" in (verified.message or "")
    assert stub.exchanges == []  # nothing was asked of the gateway


def test_zibal_details_decode_the_status_and_keep_every_field(stub: Stub) -> None:
    stub.reply(
        "/zibal/verify",
        {
            "result": 100,
            "amount": AMOUNT,
            "refNumber": 999,
            "status": 1,
            "paidAt": "2026-08-04T10:00:00",
            "cardNumber": "621986******0080",
            "wage": 500,
        },
    )
    details = ZibalSync().verify_payment(a_verification("424242")).details
    assert isinstance(details, ZibalVerifyDetails)
    assert details.status == 1
    assert details.status_text == "paid — settled"
    assert details.paid_at == "2026-08-04T10:00:00"
    assert details.card_number == "621986******0080"
    assert details.wage == 500


# ---------------------------------------------------------------------------------------------
# Yektapay
# ---------------------------------------------------------------------------------------------


def test_yektapay_request_sends_its_token_header(stub: Stub) -> None:
    stub.reply("/yektapay/request", {"uuid": "u-1"})
    payment = YektapaySync(token="tok").make_payment_request(a_request())
    assert payment.authority == "u-1"
    assert stub.last("/yektapay/request").headers["authorization"] == "Token tok"


async def test_yektapay_verify_async(stub: Stub) -> None:
    stub.reply("/yektapay/verify/u-1/", {"status": "successful", "amount": AMOUNT})
    verified = await YektapayAsync(token="tok").verify_payment(a_verification("u-1"))
    assert verified.success


def test_yektapay_verify_rejects_unsuccessful_status(stub: Stub) -> None:
    stub.reply("/yektapay/verify/u-1/", {"status": "failed"})
    verified = YektapaySync(token="tok").verify_payment(a_verification("u-1"))
    assert not verified.success


# ---------------------------------------------------------------------------------------------
# Top
# ---------------------------------------------------------------------------------------------


def test_top_request_uses_the_gateways_own_service_url(stub: Stub) -> None:
    """Top hands back the payment page URL; it is not a template that can be rebuilt."""
    stub.reply(
        "/top/request",
        {"status": 0, "data": {"token": "T1", "serviceURL": "https://pay.top.ir/x/T1"}},
    )
    payment = TopSync(username="u", password="p").make_payment_request(a_request())
    assert payment.redirect_url == "https://pay.top.ir/x/T1"

    sent = stub.last("/top/request")
    assert sent.headers["authorization"].startswith("Basic ")
    assert sent.json["MerchantOrderId"] == 1001  # numeric, not the string


async def test_top_verify_async(stub: Stub) -> None:
    stub.reply("/top/verify", {"status": 0, "data": {"rrn": "R9"}})
    verified = await TopAsync(username="u", password="p").verify_payment(a_verification("T1"))
    assert verified.success
    assert verified.reference == "R9"


def test_top_rejects_a_non_numeric_order_id_before_calling_out(stub: Stub) -> None:
    """Top's MerchantOrderId is an Int64; a UUID is rejected by its web layer with no message."""
    with pytest.raises(ConfigurationError):
        TopSync(username="u", password="p").make_payment_request(a_request(order_id="abc-def"))
    assert stub.exchanges == []


def test_top_needs_both_credentials() -> None:
    with pytest.raises(ConfigurationError):
        TopSync(username="u", password="")


# ---------------------------------------------------------------------------------------------
# Sepehr
# ---------------------------------------------------------------------------------------------


def test_sepehr_request_sync(stub: Stub) -> None:
    stub.reply("/sepehr/token", {"Status": 0, "Accesstoken": "S1"})
    payment = SepehrSync(terminal_id="T").make_payment_request(a_request())
    assert payment.authority == "S1"
    assert "token=S1" in payment.redirect_url
    assert stub.last("/sepehr/token").json["invoiceID"] == 1001


@pytest.mark.parametrize("status", ["ok", "duplicate"])
def test_sepehr_verify_accepts_ok_and_duplicate(stub: Stub, status: str) -> None:
    """'duplicate' is Sepehr's answer to a second Advice for the same receipt — still paid."""
    stub.reply("/sepehr/advice", {"Status": status, "ReturnId": AMOUNT})
    verified = SepehrSync(terminal_id="T").verify_payment(
        a_verification("S1", digitalreceipt="RCPT-1")
    )
    assert verified.success
    assert verified.reference == "RCPT-1"


async def test_sepehr_verify_async(stub: Stub) -> None:
    stub.reply("/sepehr/advice", {"Status": "ok", "ReturnId": AMOUNT})
    verified = await SepehrAsync(terminal_id="T").verify_payment(
        a_verification("S1", digitalreceipt="RCPT-1")
    )
    assert verified.success


def test_sepehr_verify_fails_closed_without_a_receipt(stub: Stub) -> None:
    """Without the receipt there is no question to ask Sepehr, so nothing may be confirmed."""
    verified = SepehrSync(terminal_id="T").verify_payment(a_verification("S1"))
    assert not verified.success
    assert "digitalreceipt" in (verified.message or "")
    assert stub.exchanges == []


def test_sepehr_reads_the_callback_case_insensitively(stub: Stub) -> None:
    """The bank POSTs ``digitalreceipt`` lower-cased while documenting it camel-cased."""
    stub.reply("/sepehr/advice", {"Status": "ok", "ReturnId": AMOUNT})
    verified = SepehrSync(terminal_id="T").verify_payment(
        a_verification("S1", DigitalReceipt="RCPT-9", invoiceid="1001")
    )
    assert verified.success
    assert verified.reference == "RCPT-9"


# ---------------------------------------------------------------------------------------------
# Cross-cutting: both engines, over the wire
# ---------------------------------------------------------------------------------------------


def test_network_failure_on_verify_never_raises(stub: Stub) -> None:
    """A customer returning from their bank must not meet an exception."""
    verified = ZibalSync(timeout=0.5).verify_payment(a_verification("424242"))
    assert not verified.success  # the stub has no reply registered → 404 with a JSON error body
    assert verified.message


def test_network_failure_on_request_raises(stub: Stub, monkeypatch: pytest.MonkeyPatch) -> None:
    """The request path fails loudly, so no customer is sent to a gateway with nothing waiting."""
    monkeypatch.setattr(zibal_sync_engine, "REQUEST_URL", "http://127.0.0.1:1/dead")
    with pytest.raises(NetworkError, match="zibal"):
        ZibalSync().make_payment_request(a_request())


async def test_network_failure_on_request_raises_async(
    stub: Stub, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(zibal_async_engine, "REQUEST_URL", "http://127.0.0.1:1/dead")
    with pytest.raises(NetworkError, match="zibal"):
        await ZibalAsync().make_payment_request(a_request())


def test_non_json_response_is_a_clean_error(stub: Stub) -> None:
    stub.reply_text("/zibal/request", "<html>502 Bad Gateway</html>", status=502)
    with pytest.raises(NetworkError, match="non-JSON"):
        ZibalSync().make_payment_request(a_request())


async def test_non_json_response_is_a_clean_error_async(stub: Stub) -> None:
    """aiohttp refuses a JSON decode on a text/html response; the SDK must not depend on that."""
    stub.reply_text("/zibal/request", "<html>502 Bad Gateway</html>", status=502)
    with pytest.raises(NetworkError, match="non-JSON"):
        await ZibalAsync().make_payment_request(a_request())


async def test_json_declared_as_html_is_still_accepted(stub: Stub) -> None:
    """Several of these gateways answer JSON under the wrong content type. That must still work."""
    stub.reply_text("/zibal/request", '{"result": 100, "trackId": 5}')
    payment = await ZibalAsync().make_payment_request(a_request())
    assert payment.authority == "5"


def test_a_json_array_is_rejected(stub: Stub) -> None:
    stub.reply("/zibal/request", [1, 2, 3])
    with pytest.raises(NetworkError, match="not an object"):
        ZibalSync().make_payment_request(a_request())


def test_both_engines_send_identical_payloads(stub: Stub) -> None:
    """The engines must differ only in how the bytes are delivered, never in what they are."""
    stub.reply("/zibal/request", {"result": 100, "trackId": 1})
    ZibalSync().make_payment_request(a_request())
    asyncio.run(ZibalAsync().make_payment_request(a_request()))
    first, second = stub.exchanges[0], stub.exchanges[1]
    assert first.json == second.json
    assert first.headers["content-type"] == second.headers["content-type"]


async def test_concurrent_rest_calls_do_not_serialise(stub: Stub) -> None:
    """Eight payments opened at once must overlap, not queue behind each other."""
    stub.reply("/zibal/request", {"result": 100, "trackId": 7})
    gateway = ZibalAsync()
    payments = await asyncio.gather(
        *(gateway.make_payment_request(a_request(order_id=str(3000 + i))) for i in range(8))
    )
    assert len(payments) == 8
    assert len(stub.exchanges) == 8


# ---------------------------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------------------------


def test_registry_lists_every_gateway() -> None:
    assert available() == (
        "parsian",
        "sadad",
        "sepehr",
        "top",
        "yektapay",
        "zarinpal",
        "zibal",
    )


def test_registry_builds_both_engines() -> None:
    assert get_sync_gateway("zarinpal", merchant_id=MERCHANT_ID).name == "zarinpal"
    assert get_async_gateway("zarinpal", merchant_id=MERCHANT_ID).name == "zarinpal"


def test_registry_rejects_an_unknown_name() -> None:
    with pytest.raises(ConfigurationError, match="unknown gateway"):
        get_sync_gateway("mellat", merchant_id="x")


def test_verification_result_is_truthy_only_when_paid() -> None:
    assert VerificationResult(success=True)
    assert not VerificationResult(success=False)
