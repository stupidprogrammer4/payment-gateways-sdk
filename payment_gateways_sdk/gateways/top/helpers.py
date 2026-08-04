"""Top / PNA — auth headers, payload building, and response reading."""

import base64
from datetime import datetime
from typing import Any

from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import GatewayError
from payment_gateways_sdk.common.utils import as_int, as_text, check_amount, numeric_order_id
from payment_gateways_sdk.gateways.top.constants import (
    NAME,
    SUCCESS_STATUS,
    TEHRAN,
    TIMESTAMP_FORMAT,
)
from payment_gateways_sdk.gateways.top.data import TopConfig, TopRequestDetails, TopVerifyDetails


def now() -> str:
    return datetime.now(TEHRAN).strftime(TIMESTAMP_FORMAT)


def auth_headers(config: TopConfig) -> dict[str, str]:
    pair = f"{config.username.strip()}:{config.password.strip()}".encode()
    return {
        "Authorization": f"Basic {base64.b64encode(pair).decode()}",
        "Content-Type": "application/json",
    }


def _body(raw: dict[str, Any]) -> dict[str, Any]:
    body = raw.get("data")
    return body if isinstance(body, dict) else {}


def build_request_payload(config: TopConfig, data: PaymentRequest) -> dict[str, Any]:
    return {
        "MerchantOrderId": numeric_order_id(data.order_id, gateway=NAME),
        "MerchantOrderDate": now(),
        "AdditionalData": data.description or "",
        "Amount": data.amount,
        "CallBackUrl": data.callback_url,
        "ReceptShowTime": 0,
        "walletCode": config.username.strip(),
        "MobileNumber": data.mobile or "",
    }


def read_request_details(raw: dict[str, Any]) -> TopRequestDetails:
    body = _body(raw)
    return TopRequestDetails(
        status=as_int(raw.get("status")),
        message=as_text(raw.get("message")),
        token=as_text(body.get("token")),
        service_url=as_text(body.get("serviceURL")),
        merchant_order_id=as_int(body.get("merchantOrderId") or body.get("MerchantOrderId")),
    )


def parse_request_response(raw: dict[str, Any]) -> PaymentResponse:
    details = read_request_details(raw)
    if details.status != SUCCESS_STATUS:
        raise GatewayError(
            f"top declined the request: {details.message or details.status}",
            code=details.status,
            raw=raw,
        )
    if not details.token or not details.service_url:
        raise GatewayError(f"top returned no token/serviceURL: {raw}", code=details.status, raw=raw)
    return PaymentResponse(
        authority=details.token, redirect_url=details.service_url, raw=raw, details=details
    )


def build_verify_payload(data: PaymentVerification) -> dict[str, Any]:
    return {
        "token": data.authority,
        "MerchantOrderId": numeric_order_id(data.order_id, gateway=NAME),
        "transactionDateTime": now(),
        "additionalData": "",
    }


def read_verify_details(raw: dict[str, Any]) -> TopVerifyDetails:
    body = _body(raw)
    return TopVerifyDetails(
        status=as_int(raw.get("status")),
        message=as_text(raw.get("message")),
        rrn=as_text(body.get("rrn") or body.get("RRN")),
        amount=as_int(body.get("amount") or body.get("Amount")),
        card_number=as_text(body.get("cardNumber") or body.get("maskedCardNumber")),
        transaction_date=as_text(body.get("transactionDate") or body.get("transactionDateTime")),
    )


def parse_verify_response(raw: dict[str, Any], data: PaymentVerification) -> VerificationResult:
    details = read_verify_details(raw)
    if details.status != SUCCESS_STATUS:
        return VerificationResult(
            success=False,
            message=f"top declined: {details.message or details.status}",
            raw=raw,
            details=details,
        )
    # ConfirmPurchase is scoped to (token, MerchantOrderId) — both ours — so it cannot confirm
    # somebody else's transaction. It does not echo a settled amount, so there is nothing here to
    # compare; if a later version carries one it is still checked.
    body = _body(raw)
    settled_amount, reason = check_amount(
        body.get("amount") or body.get("Amount"), data.amount, gateway=NAME, required=False
    )
    if reason:
        return VerificationResult(success=False, message=reason, raw=raw, details=details)
    return VerificationResult(
        success=True,
        reference=details.rrn or data.authority,
        amount=settled_amount,
        raw=raw,
        details=details,
    )
