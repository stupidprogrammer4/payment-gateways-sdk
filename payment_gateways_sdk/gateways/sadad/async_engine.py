"""Sadad, async engine."""

from payment_gateways_sdk.common.constants import DEFAULT_TIMEOUT
from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import PaymentError
from payment_gateways_sdk.common.http import apost_json
from payment_gateways_sdk.gateways.sadad.constants import NAME, REQUEST_URL, VERIFY_URL
from payment_gateways_sdk.gateways.sadad.data import SadadConfig
from payment_gateways_sdk.gateways.sadad.helpers import (
    build_request_payload,
    build_verify_payload,
    parse_request_response,
    parse_verify_response,
)


class SadadAsync:
    """Sadad over the async engine. Satisfies
    :class:`~payment_gateways_sdk.common.interfaces.IAsyncPaymentGateway`.

    Needs ``pycryptodome``: ``pip install "payment-gateways-sdk[sadad]"``.
    """

    name = NAME

    def __init__(
        self,
        merchant_id: str,
        terminal_id: str,
        terminal_key: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.config = SadadConfig(
            merchant_id=merchant_id, terminal_id=terminal_id, terminal_key=terminal_key
        )
        self.timeout = timeout

    async def make_payment_request(self, data: PaymentRequest) -> PaymentResponse:
        raw = await apost_json(
            REQUEST_URL,
            build_request_payload(self.config, data),
            gateway=self.name,
            timeout=self.timeout,
        )
        return parse_request_response(raw)

    async def verify_payment(self, data: PaymentVerification) -> VerificationResult:
        if not data.authority:
            return VerificationResult(success=False, message="missing token")
        try:
            payload = build_verify_payload(self.config, data)
            raw = await apost_json(VERIFY_URL, payload, gateway=self.name, timeout=self.timeout)
        except PaymentError as exc:
            return VerificationResult(success=False, message=str(exc))
        return parse_verify_response(raw, data)
