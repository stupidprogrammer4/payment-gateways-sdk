import base64

import pytest

from payment_gateways_sdk import (
    CardPaymentRequest,
    ConfigurationError,
    ParsianCardSync,
    ParsianSync,
    SadadCardAsync,
    SadadCardSync,
    ZarinpalCardAsync,
    ZarinpalCardSync,
    ZibalCardAsync,
    ZibalCardSync,
    ZibalSync,
    available_card_gateways,
    get_async_card_gateway,
    get_sync_card_gateway,
)
from payment_gateways_sdk.gateways.parsian.helpers import build_card_sale_request, encrypt_pan
from tests.conftest import Stub

AMOUNT = 50_000
CALLBACK = "https://shop.example/callback"
ORDER_ID = "1001"
MERCHANT_ID = "m" * 36
PAN = "6219861012340080"
AES_KEY = base64.b64encode(bytes(range(32))).decode()
AES_IV = base64.b64encode(bytes(range(16))).decode()
TERMINAL_KEY = base64.b64encode(bytes(range(24))).decode()


def a_card_request(**overrides: object) -> CardPaymentRequest:
    fields: dict[str, object] = {
        "amount": AMOUNT,
        "callback_url": CALLBACK,
        "order_id": ORDER_ID,
        "card_pan": PAN,
    }
    fields.update(overrides)
    return CardPaymentRequest(**fields)  # type: ignore[arg-type]


def test_registry_lists_only_gateways_that_support_cards() -> None:
    assert available_card_gateways() == ("parsian", "sadad", "zarinpal", "zibal")


def test_registry_rejects_a_gateway_without_card_support() -> None:
    with pytest.raises(ConfigurationError, match="does not support card payments"):
        get_sync_card_gateway("top", username="u", password="p")


def test_registry_builds_both_engines() -> None:
    assert get_sync_card_gateway("zibal", merchant="m").name == "zibal"
    assert get_async_card_gateway("zibal", merchant="m").name == "zibal"


def test_zarinpal_sends_the_pan_in_metadata(stub: Stub) -> None:
    stub.reply("/zarinpal/request", {"data": {"code": 100, "authority": "A123"}})
    payment = ZarinpalCardSync(merchant_id=MERCHANT_ID).make_card_payment_request(
        a_card_request(mobile="09120000000")
    )
    assert payment.authority == "A123"
    sent = stub.last("/zarinpal/request").json
    assert sent["metadata"]["card_pan"] == PAN
    assert sent["metadata"]["mobile"] == "09120000000"


async def test_zarinpal_card_async(stub: Stub) -> None:
    stub.reply("/zarinpal/request", {"data": {"code": 100, "authority": "A123"}})
    payment = await ZarinpalCardAsync(merchant_id=MERCHANT_ID).make_card_payment_request(
        a_card_request()
    )
    assert payment.authority == "A123"


def test_zibal_sends_allowed_cards(stub: Stub) -> None:
    stub.reply("/zibal/request", {"result": 100, "trackId": 42})
    payment = ZibalCardSync().make_card_payment_request(a_card_request(national_id="0012345678"))
    assert payment.authority == "42"
    sent = stub.last("/zibal/request").json
    assert sent["allowedCards"] == [PAN]
    assert sent["checkMobileWithCard"] is True
    assert sent["nationalCode"] == "0012345678"


def test_zibal_card_check_can_be_turned_off(stub: Stub) -> None:
    stub.reply("/zibal/request", {"result": 100, "trackId": 42})
    ZibalCardSync(check_mobile_with_card=False).make_card_payment_request(a_card_request())
    assert stub.last("/zibal/request").json["checkMobileWithCard"] is False


async def test_zibal_card_async(stub: Stub) -> None:
    stub.reply("/zibal/request", {"result": 100, "trackId": 42})
    payment = await ZibalCardAsync().make_card_payment_request(a_card_request())
    assert payment.authority == "42"
    assert stub.last("/zibal/request").json["allowedCards"] == [PAN]


def test_sadad_encrypts_the_pan_and_sets_authentication_type(stub: Stub) -> None:
    pytest.importorskip("Crypto", reason="needs the 'sadad' extra")
    stub.reply("/sadad/request", {"ResCode": 0, "Token": "T1"})
    payment = SadadCardSync(
        merchant_id="m", terminal_id="t", terminal_key=TERMINAL_KEY
    ).make_card_payment_request(a_card_request(mobile="09120000000"))
    assert payment.authority == "T1"
    sent = stub.last("/sadad/request").json
    assert sent["PanAuthenticationType"] == 2
    assert sent["SourcePanList"]["IsDefault"] is True
    assert sent["SourcePanList"]["Pan"] != PAN
    assert base64.b64decode(sent["SourcePanList"]["Pan"])
    assert sent["UserId"] == "09120000000"


async def test_sadad_card_async(stub: Stub) -> None:
    pytest.importorskip("Crypto", reason="needs the 'sadad' extra")
    stub.reply("/sadad/request", {"ResCode": 0, "Token": "T1"})
    payment = await SadadCardAsync(
        merchant_id="m", terminal_id="t", terminal_key=TERMINAL_KEY
    ).make_card_payment_request(a_card_request())
    assert payment.authority == "T1"


def test_parsian_encrypts_the_pan_into_additional_data() -> None:
    pytest.importorskip("Crypto", reason="needs the 'card' extra")
    gateway = ParsianCardSync(pin="PIN", aes_key=AES_KEY, aes_iv=AES_IV)
    request = build_card_sale_request(gateway.card_config, a_card_request())
    assert request["LoginAccount"] == "PIN"
    assert request["OrderId"] == 1001
    payload = request["AdditionalData"]
    assert payload.startswith('[{"ph": "')
    assert PAN not in payload


def test_parsian_encryption_is_deterministic() -> None:
    pytest.importorskip("Crypto", reason="needs the 'card' extra")
    config = ParsianCardSync(pin="PIN", aes_key=AES_KEY, aes_iv=AES_IV).card_config
    assert encrypt_pan(config, PAN) == encrypt_pan(config, PAN)


def test_parsian_card_gateway_demands_its_keys() -> None:
    with pytest.raises(ConfigurationError, match="aes_key"):
        ParsianCardSync(pin="PIN", aes_key="", aes_iv=AES_IV)


def test_parsian_rejects_a_bad_aes_key() -> None:
    pytest.importorskip("Crypto", reason="needs the 'card' extra")
    config = ParsianCardSync(pin="PIN", aes_key="not-base64!!", aes_iv=AES_IV).card_config
    with pytest.raises(ConfigurationError, match="aes_key"):
        encrypt_pan(config, PAN)


def test_the_plain_gateways_take_no_card_arguments() -> None:
    with pytest.raises(TypeError):
        ParsianSync(pin="PIN", aes_key=AES_KEY)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        ZibalSync(check_mobile_with_card=False)  # type: ignore[call-arg]


@pytest.mark.parametrize("bad", ["", "12345", "not-a-card", "621986101234008"])
def test_a_bad_pan_is_refused_before_any_call(stub: Stub, bad: str) -> None:
    with pytest.raises(ConfigurationError):
        ZibalCardSync().make_card_payment_request(a_card_request(card_pan=bad))
    assert stub.exchanges == []


def test_a_spaced_pan_is_normalised(stub: Stub) -> None:
    stub.reply("/zibal/request", {"result": 100, "trackId": 42})
    ZibalCardSync().make_card_payment_request(a_card_request(card_pan="6219-8610-1234-0080"))
    assert stub.last("/zibal/request").json["allowedCards"] == [PAN]
