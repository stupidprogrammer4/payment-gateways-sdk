"""Sepehr / Mabna, sync engine."""

from payment_gateways_sdk.common.constants import DEFAULT_TIMEOUT
from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import PaymentError
from payment_gateways_sdk.common.http import post_json
from payment_gateways_sdk.gateways.sepehr.constants import ADVICE_URL, NAME, RECEIPT_KEY, TOKEN_URL
from payment_gateways_sdk.gateways.sepehr.data import SepehrConfig
from payment_gateways_sdk.gateways.sepehr.helpers import (
    build_request_payload,
    build_verify_payload,
    parse_request_response,
    parse_verify_response,
    receipt_from,
)


class SepehrSync:
    name = NAME

    def __init__(self, terminal_id: str, *, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.config = SepehrConfig(terminal_id=terminal_id)
        self.timeout = timeout

    def make_payment_request(self, data: PaymentRequest) -> PaymentResponse:
        raw = post_json(
            TOKEN_URL,
            build_request_payload(self.config, data),
            gateway=self.name,
            timeout=self.timeout,
        )
        return parse_request_response(self.config, raw)

    def verify_payment(self, data: PaymentVerification) -> VerificationResult:
        receipt = receipt_from(data)
        if not receipt:
            return VerificationResult(
                success=False,
                message=(
                    f"sepehr needs {RECEIPT_KEY!r} from the callback in PaymentVerification.extra"
                ),
            )
        try:
            raw = post_json(
                ADVICE_URL,
                build_verify_payload(self.config, receipt),
                gateway=self.name,
                timeout=self.timeout,
            )
        except PaymentError as exc:
            return VerificationResult(success=False, message=str(exc))
        return parse_verify_response(raw, data, receipt)
