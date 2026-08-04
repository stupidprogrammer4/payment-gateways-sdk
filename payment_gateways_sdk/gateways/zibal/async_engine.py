"""Zibal, async engine."""

from payment_gateways_sdk.common.constants import DEFAULT_TIMEOUT
from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import PaymentError
from payment_gateways_sdk.common.http import apost_json
from payment_gateways_sdk.gateways.zibal.constants import (
    NAME,
    REQUEST_URL,
    SANDBOX_MERCHANT,
    VERIFY_URL,
)
from payment_gateways_sdk.gateways.zibal.data import ZibalConfig
from payment_gateways_sdk.gateways.zibal.helpers import (
    build_request_payload,
    build_verify_payload,
    parse_request_response,
    parse_verify_response,
)


class ZibalAsync:
    """Zibal over the async engine. Satisfies
    :class:`~payment_gateways_sdk.common.interfaces.IAsyncPaymentGateway`."""

    name = NAME

    def __init__(
        self,
        merchant: str = SANDBOX_MERCHANT,
        *,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.config = ZibalConfig(merchant=merchant)
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
        try:
            payload = build_verify_payload(self.config, data)
        except (TypeError, ValueError):
            return VerificationResult(success=False, message=f"bad trackId {data.authority!r}")
        try:
            raw = await apost_json(VERIFY_URL, payload, gateway=self.name, timeout=self.timeout)
        except PaymentError as exc:
            return VerificationResult(success=False, message=str(exc))
        return parse_verify_response(raw, data)
