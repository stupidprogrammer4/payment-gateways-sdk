"""Behavioral tests for Zibal's non-mutating payment inquiry endpoint."""

import pytest

from payment_gateways_sdk import (
    InquiryResult,
    PaymentInquiry,
    PaymentInquiryStatus,
    ZibalAsync,
    ZibalSync,
)
from tests.conftest import Stub

MERCHANT = "zibal-test-merchant"
TRACK_ID = "424242"
AMOUNT = 50_000
ORDER_ID = "1001"


def a_payment_inquiry(**overrides: object) -> PaymentInquiry:
    fields: dict[str, object] = {
        "authority": TRACK_ID,
        "amount": AMOUNT,
        "order_id": ORDER_ID,
    }
    fields.update(overrides)
    return PaymentInquiry(**fields)  # type: ignore[arg-type]


def inquiry_response(status: int, **overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "result": 100,
        "status": status,
        "amount": AMOUNT,
        "orderId": ORDER_ID,
        "refNumber": "9001",
        "trackId": int(TRACK_ID),
    }
    fields.update(overrides)
    return fields


def test_zibal_inquiry_sends_typed_reference_and_parses_verified_payment(stub: Stub) -> None:
    response = inquiry_response(1)
    stub.reply("/zibal/inquiry", response)

    result = ZibalSync(merchant=MERCHANT).inquire_payment(a_payment_inquiry())

    assert isinstance(result, InquiryResult)
    assert result.status is PaymentInquiryStatus.VERIFIED
    assert result.amount == AMOUNT
    assert result.reference == "9001"
    assert result.raw == response
    sent = stub.last("/zibal/inquiry").json
    assert sent == {"merchant": MERCHANT, "trackId": int(TRACK_ID)}


@pytest.mark.parametrize(
    ("gateway_status", "expected"),
    [
        (1, PaymentInquiryStatus.VERIFIED),
        (2, PaymentInquiryStatus.PAID_UNVERIFIED),
        (-1, PaymentInquiryStatus.PENDING),
        (3, PaymentInquiryStatus.FAILED),
        (4, PaymentInquiryStatus.FAILED),
        (5, PaymentInquiryStatus.FAILED),
        (6, PaymentInquiryStatus.FAILED),
        (7, PaymentInquiryStatus.FAILED),
        (8, PaymentInquiryStatus.FAILED),
        (9, PaymentInquiryStatus.FAILED),
        (10, PaymentInquiryStatus.FAILED),
        (11, PaymentInquiryStatus.FAILED),
        (12, PaymentInquiryStatus.FAILED),
        (15, PaymentInquiryStatus.UNKNOWN),
        (16, PaymentInquiryStatus.UNKNOWN),
        (18, PaymentInquiryStatus.UNKNOWN),
    ],
)
def test_zibal_inquiry_maps_documented_statuses(
    stub: Stub, gateway_status: int, expected: PaymentInquiryStatus
) -> None:
    stub.reply("/zibal/inquiry", inquiry_response(gateway_status))

    result = ZibalSync().inquire_payment(a_payment_inquiry())

    assert result.status is expected


async def test_zibal_inquiry_async_parses_paid_unverified(stub: Stub) -> None:
    stub.reply("/zibal/inquiry", inquiry_response(2))

    result = await ZibalAsync(merchant=MERCHANT).inquire_payment(a_payment_inquiry())

    assert result.status is PaymentInquiryStatus.PAID_UNVERIFIED
    assert result.reference == "9001"
    assert stub.last("/zibal/inquiry").json["merchant"] == MERCHANT


@pytest.mark.parametrize(
    "response_overrides",
    [
        {"amount": AMOUNT - 1},
        {"orderId": "different-order"},
    ],
)
def test_zibal_inquiry_marks_amount_or_order_mismatch_unknown(
    stub: Stub, response_overrides: dict[str, object]
) -> None:
    stub.reply("/zibal/inquiry", inquiry_response(1, **response_overrides))

    result = ZibalSync().inquire_payment(a_payment_inquiry())

    assert result.status is PaymentInquiryStatus.UNKNOWN


@pytest.mark.parametrize("response", [{"result": 201}, {"result": -1}, {"message": "unavailable"}])
def test_zibal_inquiry_fails_closed_on_unrecognized_api_response(
    stub: Stub, response: dict[str, object]
) -> None:
    stub.reply("/zibal/inquiry", response)

    result = ZibalSync().inquire_payment(a_payment_inquiry())

    assert result.status is PaymentInquiryStatus.UNKNOWN


def test_zibal_inquiry_rejects_non_numeric_track_id_without_request(stub: Stub) -> None:
    result = ZibalSync().inquire_payment(a_payment_inquiry(authority="not-a-number"))

    assert result.status is PaymentInquiryStatus.UNKNOWN
    assert stub.exchanges == []


async def test_zibal_inquiry_async_fails_closed_on_amount_mismatch(stub: Stub) -> None:
    stub.reply("/zibal/inquiry", inquiry_response(1, amount=AMOUNT + 1))

    result = await ZibalAsync().inquire_payment(a_payment_inquiry())

    assert result.status is PaymentInquiryStatus.UNKNOWN


def test_zibal_inquiry_ignores_success_body_on_http_error(stub: Stub) -> None:
    stub.reply("/zibal/inquiry", inquiry_response(1), status=503)

    result = ZibalSync().inquire_payment(a_payment_inquiry())

    assert result.status is PaymentInquiryStatus.UNKNOWN


@pytest.mark.parametrize(
    "malformed",
    [
        {"result": 100.9},
        {"status": True},
        {"status": 1.9},
        {"amount": float(AMOUNT) + 0.9},
        {"amount": True},
    ],
)
def test_zibal_inquiry_rejects_non_integer_money_or_status(
    stub: Stub, malformed: dict[str, object]
) -> None:
    response = inquiry_response(1)
    response.update(malformed)
    stub.reply("/zibal/inquiry", response)

    result = ZibalSync().inquire_payment(a_payment_inquiry())

    assert result.status is PaymentInquiryStatus.UNKNOWN


@pytest.mark.parametrize("reference", [True, 0, {}, "X"])
def test_zibal_verified_inquiry_requires_numeric_bank_reference(
    stub: Stub, reference: object
) -> None:
    stub.reply("/zibal/inquiry", inquiry_response(1, refNumber=reference))

    result = ZibalSync().inquire_payment(a_payment_inquiry())

    assert result.status is PaymentInquiryStatus.UNKNOWN
