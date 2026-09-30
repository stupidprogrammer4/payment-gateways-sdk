"""Behavioral tests for TOP's transaction enquiry endpoint."""

import base64

import pytest

from payment_gateways_sdk import (
    InquiryResult,
    PaymentInquiry,
    PaymentInquiryStatus,
    TopAsync,
    TopSync,
)
from tests.conftest import Stub

USERNAME = "merchant-user"
PASSWORD = "merchant-password"
TOKEN = "top-token-42"
AMOUNT = 50_000


def a_payment_inquiry(**overrides: object) -> PaymentInquiry:
    fields: dict[str, object] = {
        "authority": TOKEN,
        "amount": AMOUNT,
        "order_id": "order-1001",
    }
    fields.update(overrides)
    return PaymentInquiry(**fields)  # type: ignore[arg-type]


def successful_enquiry(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {"resultId": 0, "amount": AMOUNT, "transactionId": "top-ref-8"}
    data.update(overrides)
    return {"status": 0, "data": data}


def test_top_inquiry_uses_basic_auth_and_only_returns_paid_unverified(stub: Stub) -> None:
    response = successful_enquiry()
    stub.reply("/top/inquiry", response)

    result = TopSync(USERNAME, PASSWORD).inquire_payment(a_payment_inquiry())

    assert isinstance(result, InquiryResult)
    assert result.status is PaymentInquiryStatus.PAID_UNVERIFIED
    assert result.amount == AMOUNT
    assert result.reference == "top-ref-8"
    assert result.raw == response
    sent = stub.last("/top/inquiry")
    assert sent.json == {"token": TOKEN}
    assert (
        sent.headers["authorization"]
        == "Basic " + base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    )


async def test_top_inquiry_async_returns_paid_unverified(stub: Stub) -> None:
    stub.reply("/top/inquiry", successful_enquiry())

    result = await TopAsync(USERNAME, PASSWORD).inquire_payment(a_payment_inquiry())

    assert result.status is PaymentInquiryStatus.PAID_UNVERIFIED
    assert stub.last("/top/inquiry").json == {"token": TOKEN}


@pytest.mark.parametrize(
    "response",
    [
        {"status": 0, "data": {"resultId": -1, "amount": AMOUNT}},
        {"status": 0, "data": {"resultId": 0, "amount": AMOUNT - 1}},
        {"status": 1, "data": {"resultId": 0, "amount": AMOUNT}},
        {"status": 0, "data": {"resultId": 0}},
        {"status": 0, "data": {"resultId": 0, "amount": AMOUNT}},
        {"status": 0},
    ],
)
def test_top_inquiry_returns_unknown_for_ambiguous_or_mismatched_response(
    stub: Stub, response: dict[str, object]
) -> None:
    stub.reply("/top/inquiry", response)

    result = TopSync(USERNAME, PASSWORD).inquire_payment(a_payment_inquiry())

    assert result.status is PaymentInquiryStatus.UNKNOWN


async def test_top_inquiry_async_returns_unknown_for_nonzero_result_id(stub: Stub) -> None:
    stub.reply("/top/inquiry", {"status": 0, "data": {"resultId": -1, "amount": AMOUNT}})

    result = await TopAsync(USERNAME, PASSWORD).inquire_payment(a_payment_inquiry())

    assert result.status is PaymentInquiryStatus.UNKNOWN


def test_top_inquiry_ignores_success_body_on_http_error(stub: Stub) -> None:
    stub.reply("/top/inquiry", successful_enquiry(), status=400)

    result = TopSync(USERNAME, PASSWORD).inquire_payment(a_payment_inquiry())

    assert result.status is PaymentInquiryStatus.UNKNOWN
