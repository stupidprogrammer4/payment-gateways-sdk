"""Zibal, sync engine."""

from payment_gateways_sdk.common.constants import DEFAULT_TIMEOUT
from payment_gateways_sdk.common.data import (
    CardPaymentRequest,
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
from payment_gateways_sdk.gateways.zibal.data import ZibalCardConfig, ZibalConfig
from payment_gateways_sdk.gateways.zibal.helpers import (
    build_card_request_payload,
    build_request_payload,
    build_verify_payload,
    parse_request_response,
    parse_verify_response,
)


class ZibalSync:
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
        try:
            payload = build_verify_payload(self.config, data)
        except (TypeError, ValueError):
            return VerificationResult(success=False, message=f"bad trackId {data.authority!r}")
        try:
            raw = post_json(VERIFY_URL, payload, gateway=self.name, timeout=self.timeout)
        except PaymentError as exc:
            return VerificationResult(success=False, message=str(exc))
        return parse_verify_response(raw, data)


class ZibalCardSync(ZibalSync):
    def __init__(
        self,
        merchant: str = SANDBOX_MERCHANT,
        *,
        check_mobile_with_card: bool = True,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(merchant, timeout=timeout)
        self.card_config = ZibalCardConfig(
            merchant=merchant, check_mobile_with_card=check_mobile_with_card
        )

    def make_card_payment_request(self, data: CardPaymentRequest) -> PaymentResponse:
        raw = post_json(
            REQUEST_URL,
            build_card_request_payload(self.card_config, data),
            gateway=self.name,
            timeout=self.timeout,
        )
        return parse_request_response(raw)
