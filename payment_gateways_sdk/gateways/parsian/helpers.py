"""Parsian / PEC — zeep clients, request building, and result reading.

``zeep`` is the SOAP layer for both engines: :class:`zeep.Client` for the sync engine and
:class:`zeep.AsyncClient` for the async one. Both are built from the same WSDL and take the same
``requestData`` mapping, so the two engines share every decision here and differ only in the await.

**The WSDL is fetched and parsed synchronously**, by ``zeep``, on the first call for a given
(wsdl, proxy) pair — including under :class:`zeep.AsyncClient`, whose transport uses a blocking
client for the document itself. Clients are therefore cached: paying that cost once per process is
the difference between a slow first payment and a slow every payment.
"""

from typing import Any

from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import DependencyError, GatewayError
from payment_gateways_sdk.common.utils import as_int, as_text, numeric_order_id
from payment_gateways_sdk.gateways.parsian.constants import (
    NAME,
    REDIRECT_URL,
    SUCCESS_STATUS,
)
from payment_gateways_sdk.gateways.parsian.data import (
    ParsianCallbackDetails,
    ParsianConfig,
    ParsianConfirmDetails,
    ParsianSaleDetails,
)

#: Parsed WSDLs are expensive, so clients are cached per (wsdl, proxy) and per engine. Keyed by
#: proxy as well as URL, because two merchants may reach PEC by different routes.
_sync_clients: dict[tuple[str, str], Any] = {}
_async_clients: dict[tuple[str, str], Any] = {}


def _require_zeep() -> Any:
    try:
        import zeep  # noqa: PLC0415 — lazy so a missing SOAP stack takes out only this gateway
    except ImportError as exc:
        raise DependencyError(
            "the parsian gateway needs SOAP support from 'zeep' — "
            "install it with: pip install 'payment-gateways-sdk[parsian]'"
        ) from exc
    return zeep


def sync_client(config: ParsianConfig, wsdl: str) -> Any:
    """A cached :class:`zeep.Client`. Blocking: it fetches and parses the WSDL on first use."""
    proxy = config.proxy.strip()
    key = (wsdl, proxy)
    cached = _sync_clients.get(key)
    if cached is not None:
        return cached

    zeep = _require_zeep()
    transport = None
    if proxy:
        import requests  # noqa: PLC0415 — only needed when a proxy is configured

        session = requests.Session()
        session.proxies = {"http": proxy, "https": proxy}
        transport = zeep.transports.Transport(session=session)
    client = zeep.Client(wsdl, transport=transport) if transport else zeep.Client(wsdl)
    _sync_clients[key] = client
    return client


def async_client(config: ParsianConfig, wsdl: str) -> Any:
    """A cached :class:`zeep.AsyncClient`.

    Its operations are awaited, but constructing it is not: ``zeep`` reads the WSDL through a
    synchronous client even here. That happens once per (wsdl, proxy) thanks to the cache.
    """
    proxy = config.proxy.strip()
    key = (wsdl, proxy)
    cached = _async_clients.get(key)
    if cached is not None:
        return cached

    zeep = _require_zeep()
    try:
        from zeep.transports import AsyncTransport  # noqa: PLC0415 — part of the `async` extra
    except ImportError as exc:
        raise DependencyError(
            "the parsian async engine needs zeep's async transport — "
            "install it with: pip install 'payment-gateways-sdk[parsian]'"
        ) from exc

    transport: Any = None
    if proxy:
        import httpx  # noqa: PLC0415 — zeep's async transport is built on httpx

        transport = AsyncTransport(client=httpx.AsyncClient(proxy=proxy))
    client = zeep.AsyncClient(wsdl, transport=transport) if transport else zeep.AsyncClient(wsdl)
    _async_clients[key] = client
    return client


def clear_client_cache() -> None:
    """Drop every cached client. Used by the tests, which point each case at a fresh WSDL."""
    _sync_clients.clear()
    _async_clients.clear()


def redirect_url(token: int) -> str:
    return REDIRECT_URL.format(token=token)


def build_sale_request(config: ParsianConfig, data: PaymentRequest) -> dict[str, Any]:
    """The ``requestData`` mapping for ``SalePaymentRequest``.

    ``zeep`` maps this onto the WSDL's own types, so ``Amount`` and ``OrderId`` go out as the
    ``long`` the schema declares rather than as strings.
    """
    return {
        "LoginAccount": config.pin.strip(),
        "Amount": data.amount,
        "OrderId": numeric_order_id(data.order_id, gateway=NAME),
        "CallBackUrl": data.callback_url,
        "AdditionalData": data.description or "",
        "Originator": data.mobile or "",
    }


def build_confirm_request(config: ParsianConfig, token: int) -> dict[str, Any]:
    return {"LoginAccount": config.pin.strip(), "Token": token}


def read_sale_details(result: Any) -> ParsianSaleDetails:
    """``zeep`` hands back a typed object, so the fields are read as attributes."""
    return ParsianSaleDetails(
        status=as_int(getattr(result, "Status", None)),
        message=as_text(getattr(result, "Message", None)),
        token=as_int(getattr(result, "Token", None)),
    )


def parse_sale_result(result: Any) -> PaymentResponse:
    details = read_sale_details(result)
    if details.status != SUCCESS_STATUS or not details.token or details.token <= 0:
        raise GatewayError(
            f"parsian declined the request: {details.message} (status {details.status})",
            code=details.status,
        )
    return PaymentResponse(
        authority=str(details.token),
        redirect_url=redirect_url(details.token),
        details=details,
    )


def read_confirm_details(result: Any) -> ParsianConfirmDetails:
    return ParsianConfirmDetails(
        status=as_int(getattr(result, "Status", None)),
        token=as_int(getattr(result, "Token", None)),
        rrn=as_text(getattr(result, "RRN", None)),
        card_number_masked=as_text(getattr(result, "CardNumberMasked", None)),
    )


def parse_confirm_result(result: Any, data: PaymentVerification) -> VerificationResult:
    details = read_confirm_details(result)
    if details.status != SUCCESS_STATUS:
        return VerificationResult(
            success=False, message=f"parsian declined: {details.status}", details=details
        )
    # ConfirmPayment does not echo the amount — PEC exposes that on a different operation — so
    # there is nothing here to compare against. What binds this answer to this payment is the
    # token: it is the one issued when the payment was opened, and Parsian will confirm no other
    # transaction for it.
    rrn = details.rrn or read_callback(data.extra).rrn
    return VerificationResult(
        success=True,
        reference=str(rrn or data.authority),
        amount=data.amount,
        details=details,
    )


def read_callback(params: dict[str, Any]) -> ParsianCallbackDetails:
    """The bank's callback form data, typed. Field names are matched case-insensitively because
    PEC sends ``status`` lower-cased and ``Token`` capitalised in the same POST."""
    lowered = {str(key).lower(): value for key, value in params.items()}
    return ParsianCallbackDetails(
        token=as_int(lowered.get("token")),
        status=as_int(lowered.get("status")),
        rrn=as_text(lowered.get("rrn")),
        order_id=as_int(lowered.get("orderid")),
        terminal_no=as_text(lowered.get("terminalno")),
    )


def callback_declined(data: PaymentVerification) -> str | None:
    """Whether the bank already said in its callback that the customer did not pay.

    An absent status is treated as "no objection" — the Confirm call is still the deciding one, and
    refusing to ask because a descriptive field was missing would strand a payment that did arrive.
    """
    status = read_callback(data.extra).status
    if status is not None and status != SUCCESS_STATUS:
        return f"parsian callback status {status}"
    return None
