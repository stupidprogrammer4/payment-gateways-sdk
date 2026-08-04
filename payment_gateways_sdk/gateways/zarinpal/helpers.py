"""ZarinPal — URL selection, payload building, and response reading.

Everything here is a pure function over the dataclasses in ``data.py``, which is what lets the sync
and async engines share every decision and differ only in how the HTTP call is made.
"""

from typing import Any

from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import GatewayError
from payment_gateways_sdk.common.utils import as_int, as_text, check_amount
from payment_gateways_sdk.gateways.zarinpal.constants import (
    DEFAULT_DESCRIPTION,
    NAME,
    REQUEST_SUCCESS_CODE,
    REQUEST_URL,
    SANDBOX_REQUEST_URL,
    SANDBOX_START_URL,
    SANDBOX_VERIFY_URL,
    START_URL,
    VERIFY_SUCCESS_CODES,
    VERIFY_URL,
)
from payment_gateways_sdk.gateways.zarinpal.data import (
    ZarinpalConfig,
    ZarinpalRequestDetails,
    ZarinpalVerifyDetails,
)


def request_url(config: ZarinpalConfig) -> str:
    return SANDBOX_REQUEST_URL if config.sandbox else REQUEST_URL


def verify_url(config: ZarinpalConfig) -> str:
    return SANDBOX_VERIFY_URL if config.sandbox else VERIFY_URL


def start_url(config: ZarinpalConfig, authority: str) -> str:
    template = SANDBOX_START_URL if config.sandbox else START_URL
    return template.format(authority=authority)


def _body(raw: dict[str, Any]) -> dict[str, Any]:
    """ZarinPal nests everything under ``data``, and sends ``errors`` there instead on failure."""
    body = raw.get("data")
    return body if isinstance(body, dict) else {}


def build_request_payload(config: ZarinpalConfig, data: PaymentRequest) -> dict[str, Any]:
    return {
        "merchant_id": config.merchant_id.strip(),
        "amount": data.amount,
        "description": data.description or DEFAULT_DESCRIPTION,
        "callback_url": data.callback_url,
        "metadata": (
            {"order_id": data.order_id, "mobile": data.mobile}
            if (data.order_id or data.mobile)
            else {}
        ),
    }


def read_request_details(raw: dict[str, Any]) -> ZarinpalRequestDetails:
    body = _body(raw)
    return ZarinpalRequestDetails(
        code=as_int(body.get("code")),
        message=as_text(body.get("message")),
        authority=as_text(body.get("authority")),
        fee_type=as_text(body.get("fee_type")),
        fee=as_int(body.get("fee")),
    )


def parse_request_response(config: ZarinpalConfig, raw: dict[str, Any]) -> PaymentResponse:
    details = read_request_details(raw)
    if details.code != REQUEST_SUCCESS_CODE or not details.authority:
        reported = raw.get("errors") or details.message or details.code
        raise GatewayError(f"zarinpal declined the request: {reported}", code=details.code, raw=raw)
    return PaymentResponse(
        authority=details.authority,
        redirect_url=start_url(config, details.authority),
        raw=raw,
        details=details,
    )


def build_verify_payload(config: ZarinpalConfig, data: PaymentVerification) -> dict[str, Any]:
    return {
        "merchant_id": config.merchant_id.strip(),
        "amount": data.amount,
        "authority": data.authority,
    }


def read_verify_details(raw: dict[str, Any]) -> ZarinpalVerifyDetails:
    body = _body(raw)
    return ZarinpalVerifyDetails(
        code=as_int(body.get("code")),
        message=as_text(body.get("message")),
        ref_id=as_text(body.get("ref_id")),
        card_pan=as_text(body.get("card_pan")),
        card_hash=as_text(body.get("card_hash")),
        fee_type=as_text(body.get("fee_type")),
        fee=as_int(body.get("fee")),
        shaparak_fee=as_int(body.get("shaparak_fee")),
        order_id=as_text(body.get("order_id")),
    )


def parse_verify_response(raw: dict[str, Any], data: PaymentVerification) -> VerificationResult:
    details = read_verify_details(raw)
    if details.code not in VERIFY_SUCCESS_CODES:
        return VerificationResult(
            success=False,
            message=f"zarinpal declined: {raw.get('errors') or details.message or details.code}",
            raw=raw,
            details=details,
        )
    # The amount check is made by ZarinPal, and that is the stronger form: our amount is part of the
    # verify *request*, and a transaction settled for anything else comes back as error -50 rather
    # than as 100. So a 100 already means "paid, and paid this much". v4 carries no ``amount`` field
    # on verify; if a later version adds one it is still checked, because a gateway contradicting
    # itself must not settle.
    settled_amount, reason = check_amount(
        _body(raw).get("amount"), data.amount, gateway=NAME, required=False
    )
    if reason:
        return VerificationResult(success=False, message=reason, raw=raw, details=details)
    return VerificationResult(
        success=True,
        reference=details.ref_id or data.authority,
        amount=settled_amount,
        raw=raw,
        details=details,
    )
