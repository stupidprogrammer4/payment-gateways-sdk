"""ZarinPal, sync engine."""

from payment_gateways_sdk.common.constants import DEFAULT_TIMEOUT
from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import PaymentError
from payment_gateways_sdk.common.http import post_json
from payment_gateways_sdk.gateways.zarinpal.constants import NAME
from payment_gateways_sdk.gateways.zarinpal.data import ZarinpalConfig
from payment_gateways_sdk.gateways.zarinpal.helpers import (
    build_request_payload,
    build_verify_payload,
    parse_request_response,
    parse_verify_response,
    request_url,
    verify_url,
)


class ZarinpalSync:
    """ZarinPal over the sync engine. Satisfies
    :class:`~payment_gateways_sdk.common.interfaces.ISyncPaymentGateway`."""

    name = NAME

    def __init__(
        self,
        merchant_id: str,
        *,
        sandbox: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.config = ZarinpalConfig(merchant_id=merchant_id, sandbox=sandbox)
        self.timeout = timeout

    def make_payment_request(self, data: PaymentRequest) -> PaymentResponse:
        raw = post_json(
            request_url(self.config),
            build_request_payload(self.config, data),
            gateway=self.name,
            timeout=self.timeout,
        )
        return parse_request_response(self.config, raw)

    def verify_payment(self, data: PaymentVerification) -> VerificationResult:
        if not data.authority:
            return VerificationResult(success=False, message="missing authority")
        try:
            raw = post_json(
                verify_url(self.config),
                build_verify_payload(self.config, data),
                gateway=self.name,
                timeout=self.timeout,
            )
        except PaymentError as exc:
            return VerificationResult(success=False, message=str(exc))
        return parse_verify_response(raw, data)
