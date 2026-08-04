"""Yektapay — headers, payload building, and response reading."""

from typing import Any

from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import GatewayError
from payment_gateways_sdk.common.utils import as_int, as_text, check_amount
from payment_gateways_sdk.gateways.yektapay.constants import (
    DEFAULT_TITLE,
    NAME,
    START_URL,
    SUCCESS_STATUS,
    VERIFY_URL,
)
from payment_gateways_sdk.gateways.yektapay.data import (
    YektapayConfig,
    YektapayOrderDetails,
    YektapayVerifyDetails,
)


def auth_headers(config: YektapayConfig) -> dict[str, str]:
    return {
        "Authorization": f"Token {config.token.strip()}",
        "Content-Type": "application/json",
    }


def verify_url(authority: str) -> str:
    return VERIFY_URL.format(authority=authority)


def build_request_payload(config: YektapayConfig, data: PaymentRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "amount": data.amount,
        "title": data.description or DEFAULT_TITLE,
        "callback_url": data.callback_url,
    }
    if data.order_id:
        payload["order_id"] = data.order_id
    if data.mobile:
        payload["mobile"] = data.mobile
    return payload


def read_order_details(raw: dict[str, Any]) -> YektapayOrderDetails:
    return YektapayOrderDetails(
        uuid=as_text(raw.get("uuid")),
        amount=as_int(raw.get("amount")),
        title=as_text(raw.get("title")),
        status=as_text(raw.get("status")),
        callback_url=as_text(raw.get("callback_url")),
        created_at=as_text(raw.get("created_at")),
    )


def parse_request_response(raw: dict[str, Any]) -> PaymentResponse:
    details = read_order_details(raw)
    if not details.uuid:
        raise GatewayError(f"yektapay returned no order uuid: {raw}", raw=raw)
    return PaymentResponse(
        authority=details.uuid,
        redirect_url=START_URL.format(authority=details.uuid),
        raw=raw,
        details=details,
    )


def read_verify_details(raw: dict[str, Any]) -> YektapayVerifyDetails:
    return YektapayVerifyDetails(
        uuid=as_text(raw.get("uuid")),
        status=as_text(raw.get("status")),
        amount=as_int(raw.get("amount")),
        reference=as_text(raw.get("reference") or raw.get("ref_id")),
        card_number=as_text(raw.get("card_number")),
        paid_at=as_text(raw.get("paid_at")),
        description=as_text(raw.get("description")),
    )


def parse_verify_response(raw: dict[str, Any], data: PaymentVerification) -> VerificationResult:
    details = read_verify_details(raw)
    status = (details.status or "").lower()
    if status != SUCCESS_STATUS:
        return VerificationResult(
            success=False, message=f"yektapay status {status!r}", raw=raw, details=details
        )
    settled_amount, reason = check_amount(
        raw.get("amount"), data.amount, gateway=NAME, required=True
    )
    if reason:
        return VerificationResult(success=False, message=reason, raw=raw, details=details)
    return VerificationResult(
        success=True,
        reference=details.reference or data.authority,
        amount=settled_amount,
        raw=raw,
        details=details,
    )
