"""Top / PNA, sync engine."""

from payment_gateways_sdk.common.constants import DEFAULT_TIMEOUT
from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import ConfigurationError, PaymentError
from payment_gateways_sdk.common.http import post_json
from payment_gateways_sdk.gateways.top.constants import NAME, REQUEST_URL, VERIFY_URL
from payment_gateways_sdk.gateways.top.data import TopConfig
from payment_gateways_sdk.gateways.top.helpers import (
    auth_headers,
    build_request_payload,
    build_verify_payload,
    parse_request_response,
    parse_verify_response,
)


class TopSync:
    """Top over the sync engine. Satisfies
    :class:`~payment_gateways_sdk.common.interfaces.ISyncPaymentGateway`."""

    name = NAME

    def __init__(self, username: str, password: str, *, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.config = TopConfig(username=username, password=password)
        self.timeout = timeout

    def make_payment_request(self, data: PaymentRequest) -> PaymentResponse:
        raw = post_json(
            REQUEST_URL,
            build_request_payload(self.config, data),
            gateway=self.name,
            headers=auth_headers(self.config),
            timeout=self.timeout,
        )
        return parse_request_response(raw)

    def verify_payment(self, data: PaymentVerification) -> VerificationResult:
        if not data.authority:
            return VerificationResult(success=False, message="missing token")
        try:
            payload = build_verify_payload(data)
        except ConfigurationError as exc:
            return VerificationResult(success=False, message=str(exc))
        try:
            raw = post_json(
                VERIFY_URL,
                payload,
                gateway=self.name,
                headers=auth_headers(self.config),
                timeout=self.timeout,
            )
        except PaymentError as exc:
            return VerificationResult(success=False, message=str(exc))
        return parse_verify_response(raw, data)
