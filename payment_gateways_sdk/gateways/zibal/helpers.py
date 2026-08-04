"""Zibal — payload building and response reading."""

from typing import Any

from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import GatewayError
from payment_gateways_sdk.common.utils import as_int, as_text, check_amount
from payment_gateways_sdk.gateways.zibal.constants import (
    NAME,
    PAYMENT_STATUSES,
    REQUEST_SUCCESS_CODE,
    START_URL,
    VERIFY_SUCCESS_CODES,
)
from payment_gateways_sdk.gateways.zibal.data import (
    ZibalConfig,
    ZibalRequestDetails,
    ZibalVerifyDetails,
)


def start_url(track_id: str) -> str:
    return START_URL.format(track_id=track_id)


def build_request_payload(config: ZibalConfig, data: PaymentRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "merchant": config.merchant.strip(),
        "amount": data.amount,
        "callbackUrl": data.callback_url,
    }
    # Zibal takes an opaque orderId, so any reference works — including a UUID, which is the better
    # key because it leaks nothing about how many payments you have taken.
    if data.order_id:
        payload["orderId"] = data.order_id
    if data.description:
        payload["description"] = data.description
    if data.mobile:
        payload["mobile"] = data.mobile
    return payload


def read_request_details(raw: dict[str, Any]) -> ZibalRequestDetails:
    return ZibalRequestDetails(
        result=as_int(raw.get("result")),
        message=as_text(raw.get("message")),
        track_id=as_int(raw.get("trackId")),
    )


def parse_request_response(raw: dict[str, Any]) -> PaymentResponse:
    details = read_request_details(raw)
    if details.result != REQUEST_SUCCESS_CODE or details.track_id is None:
        raise GatewayError(
            f"zibal declined the request: {details.message or details.result}",
            code=details.result,
            raw=raw,
        )
    track_id = str(details.track_id)
    return PaymentResponse(
        authority=track_id, redirect_url=start_url(track_id), raw=raw, details=details
    )


def build_verify_payload(config: ZibalConfig, data: PaymentVerification) -> dict[str, Any]:
    """Zibal's trackId is numeric — a non-numeric authority raises, and the engine reports it."""
    return {"merchant": config.merchant.strip(), "trackId": int(data.authority)}


def read_verify_details(raw: dict[str, Any]) -> ZibalVerifyDetails:
    status = as_int(raw.get("status"))
    return ZibalVerifyDetails(
        result=as_int(raw.get("result")),
        message=as_text(raw.get("message")),
        amount=as_int(raw.get("amount")),
        status=status,
        status_text=PAYMENT_STATUSES.get(status) if status is not None else None,
        paid_at=as_text(raw.get("paidAt")),
        card_number=as_text(raw.get("cardNumber")),
        ref_number=as_text(raw.get("refNumber")),
        order_id=as_text(raw.get("orderId")),
        description=as_text(raw.get("description")),
        wage=as_int(raw.get("wage")),
    )


def parse_verify_response(raw: dict[str, Any], data: PaymentVerification) -> VerificationResult:
    details = read_verify_details(raw)
    if details.result not in VERIFY_SUCCESS_CODES:
        return VerificationResult(
            success=False,
            message=f"zibal declined: {details.message or details.result}",
            raw=raw,
            details=details,
        )
    # Fail closed on a missing amount: Zibal does report one, so its absence means something is
    # wrong with the response rather than that the check does not apply.
    settled_amount, reason = check_amount(
        raw.get("amount"), data.amount, gateway=NAME, required=True
    )
    if reason:
        return VerificationResult(success=False, message=reason, raw=raw, details=details)
    return VerificationResult(
        success=True,
        reference=details.ref_number or data.authority,
        amount=settled_amount,
        raw=raw,
        details=details,
    )
