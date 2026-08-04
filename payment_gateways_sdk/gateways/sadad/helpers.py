"""Sadad — 3DES signing, payload building, and response reading."""

import base64
from datetime import datetime
from typing import Any

from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import (
    ConfigurationError,
    DependencyError,
    GatewayError,
)
from payment_gateways_sdk.common.utils import as_int, as_text, check_amount, numeric_order_id
from payment_gateways_sdk.gateways.sadad.constants import (
    DES3_BLOCK_SIZE,
    NAME,
    PURCHASE_URL,
    SUCCESS_RES_CODES,
    TEHRAN,
    TIMESTAMP_FORMAT,
)
from payment_gateways_sdk.gateways.sadad.data import (
    SadadConfig,
    SadadRequestDetails,
    SadadVerifyDetails,
)


def _pkcs7_pad(data: bytes, block_size: int = DES3_BLOCK_SIZE) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len]) * pad_len


def sign(config: SadadConfig, plain_text: str) -> str:
    """3DES-ECB encrypt under the terminal key, base64 in and out.

    ECB has no IV, so the same input always produces the same signature — which is what makes the
    verify call's ``SignData(Token)`` reproducible without storing anything extra.
    """
    try:
        from Crypto.Cipher import DES3  # noqa: PLC0415 — lazy on purpose, see the module docstring
    except ImportError as exc:
        raise DependencyError(
            "the sadad gateway needs 3DES from 'pycryptodome' — "
            "install it with: pip install 'payment-gateways-sdk[sadad]'"
        ) from exc
    try:
        key = base64.b64decode(config.terminal_key.strip())
        cipher = DES3.new(key, DES3.MODE_ECB)
        encrypted = cipher.encrypt(_pkcs7_pad(plain_text.encode("utf-8")))
    except Exception as exc:  # a bad key must name itself, not surface as a raw crypto error
        raise ConfigurationError(
            f"sadad could not sign the request — is terminal_key a valid base64 3DES key? {exc}"
        ) from exc
    return base64.b64encode(encrypted).decode("utf-8")


def now() -> str:
    return datetime.now(TEHRAN).strftime(TIMESTAMP_FORMAT)


def purchase_url(token: str) -> str:
    return PURCHASE_URL.format(token=token)


def build_request_payload(config: SadadConfig, data: PaymentRequest) -> dict[str, Any]:
    # Sadad's OrderId is numeric and is echoed back on verify.
    order_id = numeric_order_id(data.order_id, gateway=NAME)
    terminal = config.terminal_id.strip()
    return {
        "MerchantId": config.merchant_id.strip(),
        "TerminalId": terminal,
        "Amount": data.amount,
        "OrderId": order_id,
        "LocalDateTime": now(),
        "ReturnUrl": data.callback_url,
        "SignData": sign(config, f"{terminal};{order_id};{data.amount}"),
    }


def read_request_details(raw: dict[str, Any]) -> SadadRequestDetails:
    return SadadRequestDetails(
        res_code=as_int(raw.get("ResCode")),
        description=as_text(raw.get("Description")),
        token=as_text(raw.get("Token")),
    )


def parse_request_response(raw: dict[str, Any]) -> PaymentResponse:
    details = read_request_details(raw)
    if raw.get("ResCode") not in SUCCESS_RES_CODES:
        raise GatewayError(
            f"sadad declined the request: {details.description or details.res_code}",
            code=details.res_code,
            raw=raw,
        )
    if not details.token:
        raise GatewayError("sadad returned no Token", code=details.res_code, raw=raw)
    return PaymentResponse(
        authority=details.token, redirect_url=purchase_url(details.token), raw=raw, details=details
    )


def build_verify_payload(config: SadadConfig, data: PaymentVerification) -> dict[str, Any]:
    return {"Token": data.authority, "SignData": sign(config, data.authority)}


def read_verify_details(raw: dict[str, Any]) -> SadadVerifyDetails:
    return SadadVerifyDetails(
        res_code=as_int(raw.get("ResCode")),
        description=as_text(raw.get("Description")),
        amount=as_int(raw.get("Amount")),
        order_id=as_int(raw.get("OrderId")),
        retrival_ref_no=as_text(raw.get("RetrivalRefNo")),
        system_trace_no=as_text(raw.get("SystemTraceNo")),
    )


def parse_verify_response(raw: dict[str, Any], data: PaymentVerification) -> VerificationResult:
    details = read_verify_details(raw)
    if raw.get("ResCode") not in SUCCESS_RES_CODES:
        return VerificationResult(
            success=False,
            message=f"sadad declined: {details.description or details.res_code}",
            raw=raw,
            details=details,
        )
    settled_amount, reason = check_amount(
        raw.get("Amount"), data.amount, gateway=NAME, required=True
    )
    if reason:
        return VerificationResult(success=False, message=reason, raw=raw, details=details)
    return VerificationResult(
        success=True,
        reference=details.retrival_ref_no or details.system_trace_no or data.authority,
        amount=settled_amount,
        raw=raw,
        details=details,
    )
