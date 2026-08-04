"""Zibal, sync engine."""

from payment_gateways_sdk.common.constants import DEFAULT_TIMEOUT
from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import PaymentError
from payment_gateways_sdk.common.http import post_json
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


class ZibalSync:
    """Zibal over the sync engine. Satisfies
    :class:`~payment_gateways_sdk.common.interfaces.ISyncPaymentGateway`."""

    name = NAME

    def __init__(
        self,
        merchant: str = SANDBOX_MERCHANT,
        *,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.config = ZibalConfig(merchant=merchant)
        self.timeout = timeout

    def make_payment_request(self, data: PaymentRequest) -> PaymentResponse:
        raw = post_json(
            REQUEST_URL,
            build_request_payload(self.config, data),
            gateway=self.name,
            timeout=self.timeout,
        )
        return parse_request_response(raw)

    def verify_payment(self, data: PaymentVerification) -> VerificationResult:
        # A non-numeric authority means the wrong value was stored, and asking Zibal about it would
        # be asking about somebody else's transaction or none at all.
        try:
            payload = build_verify_payload(self.config, data)
        except (TypeError, ValueError):
            return VerificationResult(success=False, message=f"bad trackId {data.authority!r}")
        try:
            raw = post_json(VERIFY_URL, payload, gateway=self.name, timeout=self.timeout)
        except PaymentError as exc:
            return VerificationResult(success=False, message=str(exc))
        return parse_verify_response(raw, data)
