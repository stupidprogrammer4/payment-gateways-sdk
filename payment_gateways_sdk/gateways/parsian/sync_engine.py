"""Parsian / PEC, sync engine — SOAP over :class:`zeep.Client`."""

from typing import Any

from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import GatewayError, PaymentError
from payment_gateways_sdk.gateways.parsian.constants import (
    CONFIRM_OPERATION,
    CONFIRM_WSDL,
    NAME,
    SALE_OPERATION,
    SALE_WSDL,
)
from payment_gateways_sdk.gateways.parsian.data import ParsianConfig
from payment_gateways_sdk.gateways.parsian.helpers import (
    build_confirm_request,
    build_sale_request,
    callback_declined,
    parse_confirm_result,
    parse_sale_result,
    sync_client,
)


class ParsianSync:
    """Parsian over the sync engine. Satisfies
    :class:`~payment_gateways_sdk.common.interfaces.ISyncPaymentGateway`.

    Needs ``zeep``: ``pip install "payment-gateways-sdk[parsian]"``.
    """

    name = NAME

    def __init__(self, pin: str, *, proxy: str = "") -> None:
        self.config = ParsianConfig(pin=pin, proxy=proxy)

    def _call(self, wsdl: str, operation: str, request_data: dict[str, Any]) -> Any:
        client = sync_client(self.config, wsdl)
        return getattr(client.service, operation)(requestData=request_data)

    def make_payment_request(self, data: PaymentRequest) -> PaymentResponse:
        request_data = build_sale_request(self.config, data)
        try:
            result = self._call(SALE_WSDL, SALE_OPERATION, request_data)
        except PaymentError:
            raise
        except Exception as exc:  # a SOAP/network failure is a clean gateway error
            raise GatewayError(f"parsian request failed: {exc}") from exc
        return parse_sale_result(result)

    def verify_payment(self, data: PaymentVerification) -> VerificationResult:
        if not data.authority:
            return VerificationResult(success=False, message="missing token")
        try:
            token = int(data.authority)
        except ValueError:
            return VerificationResult(success=False, message=f"bad token {data.authority!r}")
        declined = callback_declined(data)
        if declined:
            return VerificationResult(success=False, message=declined)
        try:
            result = self._call(
                CONFIRM_WSDL, CONFIRM_OPERATION, build_confirm_request(self.config, token)
            )
        except Exception as exc:  # noqa: BLE001 — verify must never crash a returning payer
            return VerificationResult(success=False, message=f"parsian confirm failed: {exc}")
        return parse_confirm_result(result, data)
