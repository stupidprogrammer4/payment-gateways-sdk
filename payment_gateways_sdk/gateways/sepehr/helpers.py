"""Sepehr / Mabna — payload building, callback reading, and response reading."""

from typing import Any

from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import GatewayError
from payment_gateways_sdk.common.utils import as_int, as_text, check_amount, numeric_order_id
from payment_gateways_sdk.gateways.sepehr.constants import (
    ADVICE_SUCCESS_STATUSES,
    NAME,
    PAY_URL,
    RECEIPT_KEY,
    TOKEN_SUCCESS_STATUS,
)
from payment_gateways_sdk.gateways.sepehr.data import (
    SepehrAdviceDetails,
    SepehrCallbackDetails,
    SepehrConfig,
    SepehrTokenDetails,
)


def pay_url(config: SepehrConfig, token: str) -> str:
    return f"{PAY_URL}?token={token}&terminalId={config.terminal_id.strip()}"


def build_request_payload(config: SepehrConfig, data: PaymentRequest) -> dict[str, Any]:
    return {
        "Amount": data.amount,
        "callbackURL": data.callback_url,
        # Sepehr echoes invoiceID back as a number, so it cannot be an opaque reference.
        "invoiceID": numeric_order_id(data.order_id, gateway=NAME),
        "terminalID": config.terminal_id.strip(),
        "payload": "",
    }


def read_token_details(config: SepehrConfig, raw: dict[str, Any]) -> SepehrTokenDetails:
    return SepehrTokenDetails(
        status=as_int(raw.get("Status")),
        access_token=as_text(raw.get("Accesstoken")),
        terminal_id=config.terminal_id.strip(),
        invoice_id=as_int(raw.get("invoiceID") or raw.get("InvoiceId")),
    )


def parse_request_response(config: SepehrConfig, raw: dict[str, Any]) -> PaymentResponse:
    details = read_token_details(config, raw)
    if details.status != TOKEN_SUCCESS_STATUS:
        raise GatewayError(
            f"sepehr declined the request: {details.status}", code=details.status, raw=raw
        )
    if not details.access_token:
        raise GatewayError("sepehr returned no Accesstoken", code=details.status, raw=raw)
    return PaymentResponse(
        authority=details.access_token,
        redirect_url=pay_url(config, details.access_token),
        raw=raw,
        details=details,
    )


def read_callback(params: dict[str, Any]) -> SepehrCallbackDetails:
    """The bank's callback form data, typed.

    Field names are matched case-insensitively: the bank POSTs ``invoiceid`` and ``digitalreceipt``
    in lower case while its own documentation writes them camel-cased, and a caller passing the
    form through untouched should not have to know which one arrived.
    """
    lowered = {str(key).lower(): value for key, value in params.items()}
    return SepehrCallbackDetails(
        digital_receipt=as_text(lowered.get("digitalreceipt")),
        invoice_id=as_int(lowered.get("invoiceid")),
        amount=as_int(lowered.get("amount")),
        rrn=as_text(lowered.get("rrn")),
        trace_number=as_text(lowered.get("tracenumber")),
        card_number=as_text(lowered.get("cardnumber")),
        issuer_bank=as_text(lowered.get("issuerbank")),
        date_paid=as_text(lowered.get("datepaid")),
        response_code=as_text(lowered.get("respcode")),
        response_message=as_text(lowered.get("respmsg")),
    )


def receipt_from(data: PaymentVerification) -> str:
    """The ``digitalreceipt`` from the callback, or empty if it was not passed through."""
    return read_callback(data.extra).digital_receipt or ""


def build_verify_payload(config: SepehrConfig, receipt: str) -> dict[str, Any]:
    return {RECEIPT_KEY: receipt, "Tid": config.terminal_id.strip()}


def read_advice_details(raw: dict[str, Any]) -> SepehrAdviceDetails:
    return SepehrAdviceDetails(
        status=as_text(raw.get("Status")),
        return_id=as_int(raw.get("ReturnId")),
        rrn=as_text(raw.get("RRN") or raw.get("rrn")),
        trace_number=as_text(raw.get("TraceNumber") or raw.get("tracenumber")),
        card_number=as_text(raw.get("CardNumber") or raw.get("cardnumber")),
        message=as_text(raw.get("Message")),
    )


def parse_verify_response(
    raw: dict[str, Any], data: PaymentVerification, receipt: str
) -> VerificationResult:
    details = read_advice_details(raw)
    status = (details.status or "").lower()
    if status not in ADVICE_SUCCESS_STATUSES:
        return VerificationResult(
            success=False, message=f"sepehr status {status!r}", raw=raw, details=details
        )
    settled_amount, reason = check_amount(
        raw.get("ReturnId"), data.amount, gateway=NAME, required=True
    )
    if reason:
        return VerificationResult(success=False, message=reason, raw=raw, details=details)
    # The receipt is the settlement reference: it is what the bank's own statement carries, and it
    # is unique per transaction.
    return VerificationResult(
        success=True, reference=receipt, amount=settled_amount, raw=raw, details=details
    )
