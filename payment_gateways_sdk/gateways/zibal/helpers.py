"""Zibal — payload building and response reading."""

from typing import Any

from payment_gateways_sdk.common.data import (
    CardPaymentRequest,
    InquiryResult,
    PaymentInquiry,
    PaymentInquiryStatus,
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import GatewayError
from payment_gateways_sdk.common.utils import as_int, as_text, check_amount, normalized_pan
from payment_gateways_sdk.gateways.zibal.constants import (
    NAME,
    PAYMENT_STATUSES,
    REQUEST_SUCCESS_CODE,
    START_URL,
    VERIFY_SUCCESS_CODES,
)
from payment_gateways_sdk.gateways.zibal.data import (
    ZibalCardConfig,
    ZibalConfig,
    ZibalInquiryDetails,
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
    if data.order_id:
        payload["orderId"] = data.order_id
    if data.description:
        payload["description"] = data.description
    if data.mobile:
        payload["mobile"] = data.mobile
    return payload


def build_card_request_payload(config: ZibalCardConfig, data: CardPaymentRequest) -> dict[str, Any]:
    payload = build_request_payload(ZibalConfig(merchant=config.merchant), data)
    payload["allowedCards"] = [normalized_pan(data.card_pan, gateway=NAME)]
    payload["checkMobileWithCard"] = config.check_mobile_with_card
    if data.national_id:
        payload["nationalCode"] = data.national_id
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
        ref_number=(
            str(reference)
            if (reference := _inquiry_integer(raw.get("refNumber"))) is not None and reference > 0
            else None
        ),
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
    reported_amount = raw.get("amount")
    if reported_amount is not None and _inquiry_integer(reported_amount) is None:
        return VerificationResult(
            success=False, message="zibal reported a non-integer amount", raw=raw, details=details
        )
    settled_amount, reason = check_amount(reported_amount, data.amount, gateway=NAME, required=True)
    if reason:
        return VerificationResult(success=False, message=reason, raw=raw, details=details)
    if data.order_id and details.order_id and details.order_id != data.order_id:
        return VerificationResult(
            success=False, message="zibal reported another order id", raw=raw, details=details
        )
    if not details.ref_number:
        return VerificationResult(
            success=False,
            message="zibal reported no valid bank reference",
            raw=raw,
            details=details,
        )
    return VerificationResult(
        success=True,
        reference=details.ref_number,
        amount=settled_amount,
        raw=raw,
        details=details,
    )


def _inquiry_integer(value: object) -> int | None:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return None


def build_inquiry_payload(config: ZibalConfig, data: PaymentInquiry) -> dict[str, Any]:
    return {"merchant": config.merchant.strip(), "trackId": int(data.authority)}


def parse_inquiry_response(raw: dict[str, Any], data: PaymentInquiry) -> InquiryResult:
    details = ZibalInquiryDetails(
        result=_inquiry_integer(raw.get("result")),
        status=_inquiry_integer(raw.get("status")),
        order_id=as_text(raw.get("orderId")),
        amount=_inquiry_integer(raw.get("amount")),
        ref_number=(
            str(reference)
            if (reference := _inquiry_integer(raw.get("refNumber"))) is not None and reference > 0
            else None
        ),
        paid_at=as_text(raw.get("paidAt")),
        verified_at=as_text(raw.get("verifiedAt")),
    )
    status = PaymentInquiryStatus.UNKNOWN
    message = as_text(raw.get("message"))
    reference = None
    amount = None
    if details.result == 100 and details.status is not None:
        if details.status == -1:
            status = PaymentInquiryStatus.PENDING
        elif details.status in range(3, 13):
            status = PaymentInquiryStatus.FAILED
        elif details.status in (1, 2):
            if details.amount != data.amount or (
                data.order_id and details.order_id != data.order_id
            ):
                message = "zibal inquiry amount or order id mismatch"
            elif details.status == 1 and not details.ref_number:
                message = "zibal verified inquiry has no bank reference"
            else:
                status = (
                    PaymentInquiryStatus.VERIFIED
                    if details.status == 1
                    else PaymentInquiryStatus.PAID_UNVERIFIED
                )
                reference = details.ref_number
                amount = details.amount
    return InquiryResult(
        status=status,
        reference=reference,
        amount=amount,
        message=message,
        raw=raw,
        details=details,
    )
