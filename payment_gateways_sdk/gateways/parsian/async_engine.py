"""Parsian / PEC, async engine — SOAP over :class:`zeep.AsyncClient`.

The two service calls are genuinely awaited: ``zeep``'s async transport issues them over an
``httpx.AsyncClient``, so nothing here parks the event loop and no worker thread is involved.

The one part that is *not* async is building the client, because ``zeep`` reads and parses the WSDL
through a synchronous client even under :class:`zeep.AsyncClient`. That happens once per
(wsdl, proxy) — the clients are cached in ``helpers`` — so it costs the first payment of a process
and nothing after it. Call :func:`warm_up` at startup to pay it before any customer is waiting.
"""

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
    async_client,
    build_confirm_request,
    build_sale_request,
    callback_declined,
    parse_confirm_result,
    parse_sale_result,
)


class ParsianAsync:
    """Parsian over the async engine. Satisfies
    :class:`~payment_gateways_sdk.common.interfaces.IAsyncPaymentGateway`.

    Needs ``zeep`` with its async transport: ``pip install "payment-gateways-sdk[parsian]"``.
    """

    name = NAME

    def __init__(self, pin: str, *, proxy: str = "") -> None:
        self.config = ParsianConfig(pin=pin, proxy=proxy)

    def warm_up(self) -> None:
        """Fetch and parse both WSDLs now, so no payment pays for it.

        This blocks — that is the point. Call it once during application startup rather than
        letting the first customer of each process wait for two WSDL documents.
        """
        async_client(self.config, SALE_WSDL)
        async_client(self.config, CONFIRM_WSDL)

    async def _call(self, wsdl: str, operation: str, request_data: dict[str, Any]) -> Any:
        client = async_client(self.config, wsdl)
        return await getattr(client.service, operation)(requestData=request_data)

    async def make_payment_request(self, data: PaymentRequest) -> PaymentResponse:
        request_data = build_sale_request(self.config, data)
        try:
            result = await self._call(SALE_WSDL, SALE_OPERATION, request_data)
        except PaymentError:
            raise
        except Exception as exc:  # a SOAP/network failure is a clean gateway error
            raise GatewayError(f"parsian request failed: {exc}") from exc
        return parse_sale_result(result)

    async def verify_payment(self, data: PaymentVerification) -> VerificationResult:
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
            result = await self._call(
                CONFIRM_WSDL, CONFIRM_OPERATION, build_confirm_request(self.config, token)
            )
        except Exception as exc:  # noqa: BLE001 — verify must never crash a returning payer
            return VerificationResult(success=False, message=f"parsian confirm failed: {exc}")
        return parse_confirm_result(result, data)
